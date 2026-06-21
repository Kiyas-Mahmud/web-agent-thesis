"""
Collection Runner
=================
Main data-collection script.  Pulls tasks from any configured parser,
replays each one inside a real Chromium browser (via BrowserReplay),
runs the annotation pipeline (metrics -> failure labels -> recovery -> reflection),
and writes final JSONL records to  dataset/collected/.

Usage
-----
    # Mind2Web, 20 tasks, headless (default)
    python src/collection_runner/collect_runner.py --source mind2web --limit 20

    # MiniWoB++ on local server at port 7860
    python src/collection_runner/collect_runner.py --source miniwob --miniwob-port 7860

    # WebArena task configs only (no live browser needed for configs; needs docker for real eval)
    python src/collection_runner/collect_runner.py --source webarena --limit 10

    # All three sources
    python src/collection_runner/collect_runner.py --source all --limit 50

    # Visible browser (useful for debugging)
    python src/collection_runner/collect_runner.py --source mind2web --limit 5 --no-headless
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── path bootstrap ──────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

# ── imports ─────────────────────────────────────────────────────────────────
from task_loader import TaskLoader, Mind2WebParser, MiniWoBParser, WebArenaParser
from task_loader.task_schema import Task

from browser_replay import BrowserReplay
from browser_replay.replay_schema import ActionLog, LogAction, ReplayConfig, ReplayStatus

from metric_computation import MetricComputer
from metric_computation.metric_schema import StepMetrics as _StepMetrics
from failure_labeling import FailureLabeler
from failure_labeling.decision_tree import classify_step as _classify_step
from recovery_generation import RecoveryEngine
from reflection_annotation import ReflectionAnnotator

from monitoring import (
    configure_logging,
    get_logger,
    ManifestManager,
    MetricsTracker,
    AlertSystem,
    AlertThresholds,
    ProgressDashboard,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("collection_runner")


# ═══════════════════════════════════════════════════════════════════════════
#  Task  ──►  ActionLog  converter
# ═══════════════════════════════════════════════════════════════════════════

def _selector_from_candidates(pos_candidates: List[Any]) -> Optional[str]:
    """
    Extract a CSS selector from a Mind2Web pos_candidates list.

    Mind2Web stores candidates as a list of JSON *strings* where each
    string is a dict whose ``attributes`` value is itself a JSON string.

    Selector priority:
      1. #id  (most reliable)
      2. tag.first-class
      3. tag  (last resort)
    """
    if not pos_candidates:
        return None

    # Each candidate may be a JSON string or already a dict
    raw = pos_candidates[0]
    if isinstance(raw, str):
        try:
            cand = json.loads(raw)
        except json.JSONDecodeError:
            return None
    else:
        cand = raw

    # attributes field is also frequently a JSON string
    attrs_raw = cand.get("attributes", {})
    if isinstance(attrs_raw, str):
        try:
            attrs_raw = json.loads(attrs_raw)
        except json.JSONDecodeError:
            attrs_raw = {}

    tag = (cand.get("tag") or cand.get("tag_name") or "").lower().strip()
    id_ = str(attrs_raw.get("id", "")).strip()
    cls = str(attrs_raw.get("class", "")).strip()

    if id_:
        return f"#{id_}"
    if cls:
        first_cls = cls.split()[0]
        return f"{tag}.{first_cls}" if tag else f".{first_cls}"
    return tag or None


def task_to_action_log(task: Task) -> ActionLog:
    """
    Convert a parser Task to an ActionLog that BrowserReplay can execute.

    Mind2Web tasks carry raw action dicts in
    ``task.metadata.additional_info["raw_actions"]``.

    MiniWoB / WebArena tasks have no raw_actions; we emit a minimal
    NAVIGATE + WAIT log so BrowserReplay still captures a screenshot
    trajectory (useful for load-state inspection).
    """
    raw_actions: List[Dict[str, Any]] = (
        task.metadata.additional_info.get("raw_actions", [])
    )

    log_actions: List[LogAction] = [
        # Always start by navigating to the page
        LogAction(
            action_type="NAVIGATE",
            value=task.start_url,
            description=f"Open {task.start_url}",
        ),
        LogAction(
            action_type="WAIT",
            timeout=2000,
            description="Wait for initial page load",
        ),
    ]

    _OP_MAP = {
        "CLICK":    "CLICK",
        "TYPE":     "TYPE",
        "SELECT":   "SELECT",
        "SCROLL":   "SCROLL",
        "NAVIGATE": "NAVIGATE",
        "HOVER":    "HOVER",
    }

    for raw in raw_actions:
        # op field can be a dict  {op: "CLICK", value: "..."} or just a string
        if isinstance(raw, dict):
            op_raw = raw.get("op") or raw.get("action_type") or raw.get("type") or "CLICK"
        else:
            op_raw = str(raw)

        op = _OP_MAP.get(str(op_raw).upper(), "CLICK")

        value = (
            raw.get("value")
            or raw.get("typed_text")
            or raw.get("text")
            if isinstance(raw, dict) else None
        )
        target = _selector_from_candidates(
            raw.get("pos_candidates", []) if isinstance(raw, dict) else []
        )

        log_actions.append(LogAction(
            action_type=op,
            target=target,
            value=value,
            description=raw.get("description") if isinstance(raw, dict) else None,
        ))

    # Ensure start_url is a resolvable address.
    # Mind2Web stores website as a bare name e.g. "united" → add ".com"
    start_url = task.start_url
    if start_url and "://" in start_url:
        host = start_url.split("://", 1)[1].split("/")[0]
        if "." not in host:          # no TLD → e.g. "united"
            start_url = start_url.replace(f"://{host}", f"://{host}.com", 1)

    return ActionLog(
        task_id=task.task_id,
        start_url=start_url,
        task_description=task.task_description,
        source=task.metadata.source.value,
        actions=log_actions,
        metadata={
            "domain": task.website_domain,
            "difficulty": task.metadata.difficulty.value if task.metadata.difficulty else None,
            "category": task.metadata.category.value if task.metadata.category else None,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Annotation helpers  (mirrors CollectionOrchestrator's _annotate_* methods)
# ═══════════════════════════════════════════════════════════════════════════

def _annotate_metrics(
    trajectory: Dict[str, Any],
    metric_computer: MetricComputer,
) -> Dict[str, Any]:
    """Add visual / state-hash / performance metrics to every step."""
    for i, step in enumerate(trajectory.get("steps", [])):
        sb = step.get("screenshot_before")
        sa = step.get("screenshot_after")
        exec_ms = step.get("result", {}).get("execution_time_ms", 0.0)
        if sb and sa:
            try:
                m = metric_computer.compute_step_metrics(
                    step_id=i,
                    before_screenshot=sb,
                    after_screenshot=sa,
                    execution_time_ms=exec_ms,
                )
                step["metrics"] = {
                    "visual":      m.visual.model_dump(),
                    "state_hash":  m.state_hash.model_dump(),
                    "performance": m.performance.model_dump(),
                }
            except Exception as exc:
                logger.debug(f"Metrics step {i}: {exc}")
                step["metrics"] = {"visual": {}, "state_hash": {},
                                   "performance": {"execution_time_ms": exec_ms}}
        else:
            step["metrics"] = {"visual": {}, "state_hash": {},
                               "performance": {"execution_time_ms": exec_ms}}
    return trajectory


def _annotate_failure(
    trajectory: Dict[str, Any],
    _failure_labeler,           # kept for API compatibility
) -> Dict[str, Any]:
    """Classify each step with the ordered failure decision tree.

    Decision order (first rule that fires wins):
      1. TOOL_FAILURE      - browser/network error
      2. STATE_NO_CHANGE   - pixel_diff < threshold, SSIM high, URL same
      3. LOOP_DETECTED     - same URL/state repeated >= N times
      4. PERCEPTION_ERROR  - element not found / not visible
      5. ACTION_MISMATCH   - wrong page navigated to
      6. GOAL_MISALIGNMENT - action diverges from task goal
      7. REASONING_ERROR   - failed with no clear sensor signal
      8. UNKNOWN           - none of the above
    """
    steps       = trajectory.get("steps", [])
    task_desc   = trajectory.get("task_description", "")

    for i, step in enumerate(steps):
        history = steps[:i]   # previous steps for loop detection
        try:
            clf = _classify_step(step, history=history, task_description=task_desc)
            d   = clf.to_dict()
            step["failure"] = {
                "failure_type":      d["failure_type"],
                "execution_outcome": d["execution_outcome"],
                "confidence":        d["confidence"],
                "severity":          d["severity"],
                "recoverable":       d["recoverable"],
                "explanation":       d["explanation"],
                "signals_fired":     d["signals_fired"],
                "recovery_strategy": d["recovery_strategy"],
            }
        except Exception as exc:
            logger.debug(f"Decision tree step {i}: {exc}")
            success = (step.get("result") or {}).get("success", True)
            step["failure"] = {
                "failure_type":      "none" if success else "unknown",
                "execution_outcome": "success" if success else "failure",
                "confidence":        1.0 if success else 0.0,
                "severity":          "low",
                "recoverable":       False,
                "explanation":       str(exc),
                "signals_fired":     [],
                "recovery_strategy": None if success else "RETRY",
            }
    return trajectory


def _annotate_recovery(
    trajectory: Dict[str, Any],
    _recovery_engine,   # kept for API compatibility
) -> Dict[str, Any]:
    """
    Detect and track actual recovery attempts in the trajectory.
    
    For each failed step, scans the next 1-3 steps to detect:
    - recovery_attempted: whether recovery was tried
    - recovery_method: RETRY | ALTERNATIVE_TARGET | BACKTRACK | WAIT_AND_RETRY
    - recovery_step_span: [failure_step_id, last_recovery_step_id]
    - recovery_success: True if any step in span succeeded
    - recovery_duration_ms: total time taken for recovery
    """
    steps = trajectory.get("steps", [])
    
    for i, step in enumerate(steps):
        failure = step.get("failure") or {}
        ftype = failure.get("failure_type") or "none"
        strategy = failure.get("recovery_strategy")
        
        # Initialize recovery fields
        recovery_data = {
            "attempted": False,
            "strategy": strategy,
            "method": None,
            "step_span": None,
            "success": None,
            "duration_ms": 0,
        }
        
        # If step failed, scan next few steps for recovery attempts
        if ftype != "none" and i + 1 < len(steps):
            recovery_data = _detect_recovery_attempt(step, steps, i)
        
        step["recovery"] = recovery_data
    
    return trajectory


def _detect_recovery_attempt(
    failed_step: Dict[str, Any],
    all_steps: List[Dict[str, Any]],
    failure_index: int,
) -> Dict[str, Any]:
    """
    Detect recovery attempt by analyzing subsequent steps after a failure.
    
    Returns recovery metadata dict with:
    - attempted, method, step_span, success, duration_ms
    """
    failure_step_id = failed_step.get("step_id")
    failed_action = failed_step.get("action") or {}
    failed_action_type = failed_action.get("action_type", "").upper()
    failed_target = failed_action.get("target")
    failed_value = failed_action.get("value")
    
    # Look ahead up to 3 steps for recovery
    recovery_span = []
    recovery_method = None
    total_duration = 0
    any_success = False
    
    for i in range(failure_index + 1, min(failure_index + 4, len(all_steps))):
        next_step = all_steps[i]
        next_action = next_step.get("action") or {}
        next_action_type = next_action.get("action_type", "").upper()
        next_target = next_action.get("target")
        next_value = next_action.get("value")
        next_result = next_step.get("result") or {}
        next_success = next_result.get("success", False)
        
        # Determine if this step is a recovery attempt
        is_recovery = False
        detected_method = None
        
        # RETRY: Same action type and target
        if (next_action_type == failed_action_type and
            next_target == failed_target):
            is_recovery = True
            detected_method = "RETRY"
        
        # ALTERNATIVE_TARGET: Same action type but different target
        elif (next_action_type == failed_action_type and
              next_target != failed_target and
              next_target is not None):
            is_recovery = True
            detected_method = "ALTERNATIVE_TARGET"
        
        # WAIT_AND_RETRY: WAIT action followed by retry
        elif next_action_type == "WAIT":
            is_recovery = True
            detected_method = "WAIT_AND_RETRY"
        
        # BACKTRACK: NAVIGATE back or clicking back button
        elif next_action_type == "NAVIGATE":
            # Check if navigating back to previous URL
            next_url = next_action.get("value")
            failed_url_before = failed_step.get("url_before")
            if next_url and failed_url_before and next_url == failed_url_before:
                is_recovery = True
                detected_method = "BACKTRACK"
        
        if is_recovery:
            recovery_span.append(next_step.get("step_id"))
            if recovery_method is None:
                recovery_method = detected_method
            total_duration += next_result.get("execution_time_ms", 0)
            
            if next_success:
                any_success = True
                # Stop scanning after first success
                break
        else:
            # If we see a non-recovery action, stop scanning
            # (agent moved on to something else)
            if recovery_span:
                break
    
    # Build recovery metadata
    if recovery_span:
        return {
            "attempted": True,
            "strategy": failed_step.get("failure", {}).get("recovery_strategy"),
            "method": recovery_method,
            "step_span": [failure_step_id, recovery_span[-1]],
            "success": any_success,
            "duration_ms": total_duration,
        }
    else:
        # No recovery detected - agent did not attempt recovery
        return {
            "attempted": False,
            "strategy": failed_step.get("failure", {}).get("recovery_strategy"),
            "method": None,
            "step_span": None,
            "success": None,
            "duration_ms": 0,
        }


def _annotate_reflection(
    trajectory: Dict[str, Any],
    reflector: ReflectionAnnotator,
) -> Dict[str, Any]:
    """Generate per-step reflections and merge into trajectory steps."""
    steps = trajectory.get("steps", [])
    try:
        annotations = reflector.annotate_trajectory(trajectory)
        # annotate_trajectory returns List[ReflectionAnnotation]
        if isinstance(annotations, list):
            ann_by_id: Dict[int, Any] = {}
            for ann in annotations:
                sid = getattr(ann, "step_id", None)
                if sid is not None:
                    ann_by_id[sid] = ann

            for j, step in enumerate(steps):
                step_id = step.get("step_id", j)
                ann = ann_by_id.get(step_id) or ann_by_id.get(j)
                if ann is not None:
                    try:
                        step["reflection"] = ann.model_dump()
                    except Exception:
                        step["reflection"] = {
                            "reflection_text": getattr(ann, "reflection_text", ""),
                            "agent_confidence_before": getattr(ann, "agent_confidence_before", 0.0),
                            "agent_confidence_after":  getattr(ann, "agent_confidence_after",  0.0),
                            "memory_update_flag": getattr(ann, "memory_update_flag", False),
                        }
                else:
                    step.setdefault("reflection", {"reflection_text": "", "agent_confidence_before": 0.0})
        elif isinstance(annotations, dict):
            return annotations   # reflector returned a full annotated trajectory
    except Exception as exc:
        logger.debug(f"Reflection annotation: {exc}")
        for step in steps:
            step.setdefault("reflection", {"reflection_text": "", "agent_confidence_before": 0.0})
    return trajectory


# ═══════════════════════════════════════════════════════════════════════════
#  CollectionRunner
# ═══════════════════════════════════════════════════════════════════════════

class CollectionRunner:
    """
    End-to-end data-collection orchestrator.

    Flow
    ────
    1. Load tasks from the selected parser (Mind2Web / MiniWoB / WebArena)
    2. For each task:
       a. Convert Task → ActionLog
       b. BrowserReplay.replay_task(log)  →  JSONL trajectory on disk
       c. Annotate with metrics, failure labels, recovery, reflection
       d. Append final record to  dataset/collected/<source>.jsonl
    3. Print a concise summary report
    """

    def __init__(
        self,
        output_dir: str = "dataset",
        headless: bool = True,
        step_delay_ms: int = 500,
        timeout_ms: int = 30_000,
        miniwob_port: int = 7860,
        debug: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.collected_dir = self.output_dir / "collected"
        self.collected_dir.mkdir(parents=True, exist_ok=True)

        # ── Monitoring (must be first so all logs go to the run file) ──
        import uuid
        self._run_id = f"run_{uuid.uuid4().hex[:8]}"
        configure_logging(
            run_id  = self._run_id,
            log_dir = str(self.output_dir / "logs"),
            debug   = debug,
        )
        self._manifest = ManifestManager(
            run_id     = self._run_id,
            output_dir = str(self.output_dir),
            config     = {
                "headless":      headless,
                "step_delay_ms": step_delay_ms,
                "timeout_ms":    timeout_ms,
                "miniwob_port":  miniwob_port,
                "debug":         debug,
            },
        )
        self._manifest.save()    # initial save (no results yet)
        self._tracker  = MetricsTracker(output_dir=str(self.output_dir))
        self._alerts   = AlertSystem(output_dir=str(self.output_dir))
        self._log      = get_logger("CollectionRunner")

        # Browser replay engine
        replay_cfg = ReplayConfig(
            headless=headless,
            step_delay_ms=step_delay_ms,
            timeout_ms=timeout_ms,
            output_dir=str(self.output_dir),
            continue_on_step_error=True,
        )
        self.replay = BrowserReplay(replay_cfg)
        self.miniwob_port = miniwob_port

        # Annotation pipeline
        self.metric_computer  = MetricComputer(output_dir=str(self.output_dir))
        self.failure_labeler  = FailureLabeler(metric_computer=self.metric_computer)
        self.recovery_engine  = RecoveryEngine()
        self.reflector        = ReflectionAnnotator()

        self._log.info(f"CollectionRunner ready  run_id={self._run_id}  output={self.output_dir}")
        logger.info(f"CollectionRunner ready  ->  output: {self.output_dir}")

    # ──────────────────────────────────────────────────────────────
    #  Task loading
    # ──────────────────────────────────────────────────────────────

    def _load_tasks(self, source: str, limit: int) -> List[Task]:
        """Load tasks from the requested source."""
        logger.info(f"Loading tasks  source={source!r}  limit={limit}")
        cache_dir = str(self.output_dir / "cache")

        if source == "mind2web":
            parser = Mind2WebParser(cache_dir=cache_dir, task_limit=limit)
        elif source == "miniwob":
            parser = MiniWoBParser(cache_dir=cache_dir, task_limit=limit,
                                   port=self.miniwob_port)
        elif source == "webarena":
            parser = WebArenaParser(cache_dir=cache_dir, task_limit=limit)
        elif source == "all":
            tasks: List[Task] = []
            per = max(1, limit // 3)
            for src in ("mind2web", "miniwob", "webarena"):
                tasks.extend(self._load_tasks(src, per))
            return tasks[:limit]
        else:
            raise ValueError(f"Unknown source: {source!r}. "
                             "Choose from mind2web, miniwob, webarena, all.")

        tasks = parser.parse()
        logger.info(f"  Loaded {len(tasks)} tasks from {source}")
        return tasks

    # ──────────────────────────────────────────────────────────────
    #  Trajectory loading & saving
    # ──────────────────────────────────────────────────────────────

    def _load_trajectory(self, path: str) -> Optional[Dict[str, Any]]:
        """Load a trajectory from a JSON or JSONL file written by BrowserReplay."""
        p = Path(path)
        if not p.exists():
            return None
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return None
        # Try parsing as a single JSON object first (pretty-printed)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # Fall back: take the first non-empty line (true JSONL)
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return None

    def _save_annotated(self, trajectory: Dict[str, Any], source: str) -> Path:
        """Append annotated data to two JSONL files:
        1. <source>.jsonl          - full trajectory record (for research/inspection)
        2. <source>_training.jsonl - flat per-step records (training-ready format)
        """
        # ── 1. Full trajectory JSONL ──────────────────────────────────────
        out = self.collected_dir / f"{source}.jsonl"
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(trajectory, ensure_ascii=False) + "\n")

        # ── 2. Flat per-step training JSONL ───────────────────────────────
        train_out = self.collected_dir / f"{source}_training.jsonl"
        task_id   = trajectory.get("task_id", "unknown")
        with train_out.open("a", encoding="utf-8") as fh:
            for step in trajectory.get("steps", []):
                vis        = (step.get("metrics") or {}).get("visual") or {}
                failure    = step.get("failure")    or {}
                recovery   = step.get("recovery")   or {}
                reflection = step.get("reflection") or {}
                action     = step.get("action")     or {}
                result     = step.get("result")     or {}
                flat = {
                    # ── Identity ────────────────────────────────────────
                    "task_id":  task_id,
                    "step_id":  step.get("step_id"),
                    # ── Visual state ────────────────────────────────────
                    "state_before": step.get("screenshot_before"),
                    "state_after":  step.get("screenshot_after"),
                    "pixel_diff":   vis.get("pixel_diff_score"),
                    "ssim":         vis.get("ssim_score"),
                    # ── Navigation ──────────────────────────────────────
                    "url_before":   step.get("url_before"),
                    "url_after":    step.get("url_after"),
                    # ── Action ──────────────────────────────────────────
                    "action_type":         action.get("action_type"),
                    "action_target_desc":  action.get("target"),
                    "action_value":        action.get("value"),
                    "action_coordinates":  action.get("coordinates"),
                    # ── Outcome ─────────────────────────────────────────
                    "execution_outcome":  failure.get(
                        "execution_outcome",
                        "success" if result.get("success", True) else "failure"
                    ),
                    "failure_type":       failure.get("failure_type", "none"),
                    "failure_confidence": failure.get("confidence", 0.0),
                    "failure_explanation":failure.get("explanation", ""),
                    # ── Recovery ────────────────────────────────────────
                    "recovery_strategy":  failure.get("recovery_strategy"),
                    "recovery_success":   recovery.get("success"),
                    # ── Reflection ──────────────────────────────────────
                    "agent_confidence_before": (
                        reflection.get("agent_confidence_before")
                        or reflection.get("confidence_before")
                    ),
                    "reflection_text": reflection.get("reflection_text", ""),
                }
                fh.write(json.dumps(flat, ensure_ascii=False) + "\n")
        return out

    # ──────────────────────────────────────────────────────────────
    #  Annotation pipeline
    # ──────────────────────────────────────────────────────────────

    def _annotate(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        trajectory = _annotate_metrics(trajectory, self.metric_computer)
        trajectory = _annotate_failure(trajectory, self.failure_labeler)
        trajectory = _annotate_recovery(trajectory, self.recovery_engine)
        trajectory = _annotate_reflection(trajectory, self.reflector)
        trajectory["annotated_at"] = datetime.now(timezone.utc).isoformat()
        return trajectory

    # ──────────────────────────────────────────────────────────────
    #  Main run loop
    # ──────────────────────────────────────────────────────────────

    def run(
        self,
        source: str = "mind2web",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Run the collection loop.

        Parameters
        ──────────
        source : "mind2web" | "miniwob" | "webarena" | "all"
        limit  : maximum number of tasks to process

        Returns
        ───────
        Summary dict with counts and output paths.
        """
        tasks = self._load_tasks(source, limit)
        total = len(tasks)
        if total == 0:
            logger.warning("No tasks loaded — nothing to do.")
            return {"tasks_attempted": 0}

        stats = {
            "tasks_attempted": total,
            "tasks_replayed":  0,
            "tasks_annotated": 0,
            "tasks_saved":     0,
            "tasks_failed":    0,
            "output_paths":    [],
            "started_at":      datetime.now(timezone.utc).isoformat(),
        }

        t0 = time.time()
        dashboard = ProgressDashboard(
            total_tasks = total,
            run_id      = self._run_id,
            output_dir  = str(self.output_dir),
        )
        dashboard.start()

        for idx, task in enumerate(tasks, 1):
            task_src  = task.metadata.source.value
            task_t0   = time.time()
            print(f"\n[{idx}/{total}]  {task.task_id}  ({task_src})")
            print(f"  Goal : {task.task_description[:90]}")
            print(f"  URL  : {task.start_url}")

            # ── Monitoring: task start ───────────────────────────────────
            self._tracker.task_started(task.task_id, source=task_src)
            self._log.task_start(task.task_id, source=task_src, url=task.start_url)

            # ── 1. Convert Task → ActionLog ──────────────────────────────
            try:
                action_log = task_to_action_log(task)
                n_actions = len(action_log.actions)
                print(f"  Steps: {n_actions} actions")
            except Exception as exc:
                self._log.error(f"ActionLog build failed: {exc}", task_id=task.task_id)
                self._tracker.task_finished(task.task_id, status="failed",
                                            duration_s=time.time()-task_t0,
                                            error_msg=str(exc))
                stats["tasks_failed"] += 1
                continue

            # ── 2. Replay in browser ─────────────────────────────────────
            try:
                replay_result = self.replay.replay_task(action_log)
                stats["tasks_replayed"] += 1
                status_str = replay_result.status.value
                print(f"  Replay: {status_str}  "
                      f"({replay_result.successful_steps}/{replay_result.total_steps} steps ok)  "
                      f"{replay_result.replay_duration_s:.1f}s")

                # Record each step in tracker
                for sr in replay_result.step_results:
                    self._tracker.step_done(
                        task_id     = task.task_id,
                        action_type = sr.action_type,
                        success     = sr.status.value == "success",
                        ms          = sr.execution_time_ms,
                        target      = sr.target,
                        error_msg   = sr.error_message,
                        step_index  = sr.step_index,
                    )
            except Exception as exc:
                self._log.error(f"Replay crashed: {exc}", task_id=task.task_id)
                self._tracker.task_finished(task.task_id, status="failed",
                                            duration_s=time.time()-task_t0,
                                            error_msg=str(exc))
                stats["tasks_failed"] += 1
                continue

            # ── 3. Load trajectory from disk ─────────────────────────────
            traj = None
            if replay_result.trajectory_file:
                traj = self._load_trajectory(replay_result.trajectory_file)

            if traj is None:
                traj = _build_minimal_trajectory(task, replay_result)
            else:
                # Ensure top-level status field is present
                traj.setdefault("status", replay_result.status.value)
                traj.setdefault("source", task.metadata.source.value)

            # ── 4. Annotate ──────────────────────────────────────────────
            try:
                traj = self._annotate(traj)
                stats["tasks_annotated"] += 1
                print(f"  Annotation: OK  ({len(traj.get('steps', []))} steps)")
            except Exception as exc:
                self._log.warning(f"Annotation error (saving unannotated): {exc}",
                                  task_id=task.task_id)

            # ── 5. Save ──────────────────────────────────────────────────
            try:
                out_path = self._save_annotated(traj, task_src)
                stats["tasks_saved"] += 1
                path_str = str(out_path)
                if path_str not in stats["output_paths"]:
                    stats["output_paths"].append(path_str)
                print(f"  Saved  -> {out_path}")
            except Exception as exc:
                self._log.error(f"Save error: {exc}", task_id=task.task_id)
                stats["tasks_failed"] += 1

            # ── Monitoring: task finish ──────────────────────────────────
            task_status = replay_result.status.value   # success/partial/failed
            dur = time.time() - task_t0
            self._tracker.task_finished(
                task.task_id,
                status     = task_status,
                duration_s = dur,
            )
            self._log.task_end(task.task_id, status=task_status,
                               steps=replay_result.total_steps, dur_s=dur)

            # ── Alerts check every task ──────────────────────────────────
            counters = self._tracker.summary()
            size_gb  = MetricsTracker.dataset_size_gb(self.output_dir)
            self._alerts.check(counters, dataset_size_gb=size_gb)

            # ── Dashboard refresh ────────────────────────────────────────
            dashboard.update(
                counters,
                self._tracker.recent_completed(5),
            )

        # ── Finalise ─────────────────────────────────────────────────────
        stats["total_duration_s"] = round(time.time() - t0, 2)
        stats["finished_at"] = datetime.now(timezone.utc).isoformat()

        final_counters = self._tracker.summary()
        self._manifest.finalise(final_counters)
        self._manifest.save()
        try:
            dashboard.finish(final_counters)
        except Exception as _dash_err:
            logger.debug(f"Dashboard render error (non-fatal): {_dash_err}")

        _write_quality_report(stats, self.collected_dir)
        _print_summary(stats)
        return stats


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _write_quality_report(
    stats: Dict[str, Any],
    collected_dir: Path,
) -> None:
    """Parse all *_training.jsonl files and print a publication-ready
    quality summary covering all 6 required metrics:
      - % SUCCESS / FAILURE
      - % each failure type
      - % UNKNOWN  (target < 10%)
      - % recovery success
      - avg pixel_diff
      - avg steps per task
    """
    import collections as _collections

    all_steps: List[Dict[str, Any]] = []
    for p in sorted(collected_dir.glob("*_training.jsonl")):
        for raw_line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            raw_line = raw_line.strip()
            if raw_line:
                try:
                    all_steps.append(json.loads(raw_line))
                except Exception:
                    pass

    if not all_steps:
        return

    total   = len(all_steps)
    outcomes = _collections.Counter(s.get("execution_outcome", "?") for s in all_steps)
    failure_types = _collections.Counter(
        s.get("failure_type", "unknown")
        for s in all_steps
        if (s.get("execution_outcome") or "") != "success"
    )
    recoverable = [s for s in all_steps if s.get("recovery_strategy") is not None]
    recovered   = sum(1 for s in recoverable if s.get("recovery_success") is True)
    pixel_diffs = [s["pixel_diff"] for s in all_steps
                   if s.get("pixel_diff") is not None]
    steps_per_task = _collections.Counter(s.get("task_id", "?") for s in all_steps)
    unknown_count  = failure_types.get("unknown", 0)
    n_failed       = sum(1 for s in all_steps
                         if (s.get("execution_outcome") or "") != "success")

    sep = "=" * 64
    print()
    print(sep)
    print("  DATASET QUALITY REPORT")
    print(sep)
    print(f"  Steps total          : {total}")
    for outcome, count in sorted(outcomes.items()):
        print(f"    {outcome:<20}: {count:5d}  ({count/total:.0%})")
    print()
    print(f"  Failure type breakdown  ({n_failed} failed steps):")
    for ft, count in failure_types.most_common():
        pct = count / max(1, n_failed)
        bar = '#' * int(pct * 30)
        print(f"    {ft:<22}: {count:4d}  ({pct:.0%})  {bar}")
    print()
    unknown_pct = unknown_count / max(1, n_failed)
    flag = "OK" if unknown_pct < 0.10 else "!! ABOVE TARGET"
    print(f"  UNKNOWN rate         : {unknown_pct:.1%}  (target <10%)  [{flag}]")
    print()
    if recoverable:
        print(f"  Recovery success     : {recovered}/{len(recoverable)}"
              f"  ({recovered/len(recoverable):.0%})")
    else:
        print("  Recovery success     : n/a (no failed steps)")
    if pixel_diffs:
        print(f"  Avg pixel_diff       : {sum(pixel_diffs)/len(pixel_diffs):.4f}")
    print(f"  Avg steps / task     : {total / max(1, len(steps_per_task)):.1f}")
    print(f"  Tasks in report      : {len(steps_per_task)}")
    print(sep)
    print()


def _build_minimal_trajectory(
    task: Task,
    replay_result,
) -> Dict[str, Any]:
    """
    Construct a trajectory dict from TaskReplayResult step data
    when BrowserReplay did not produce a JSONL file on disk.
    """
    steps = []
    for sr in replay_result.step_results:
        steps.append({
            "step_number": sr.step_index,
            "action": {
                "action_type": sr.action_type,
                "target": sr.target,
            },
            "screenshot_before": sr.screenshot_before,
            "screenshot_after":  sr.screenshot_after,
            "url_before":        sr.url_before,
            "url_after":         sr.url_after,
            "result": {
                "success": sr.status.value == "success",
                "error":   sr.error_message,
                "execution_time_ms": sr.execution_time_ms,
            },
        })

    return {
        "task_id":          task.task_id,
        "task_description": task.task_description,
        "start_url":        task.start_url,
        "source":           task.metadata.source.value,
        "status":           replay_result.status.value,
        "total_steps":      replay_result.total_steps,
        "successful_steps": replay_result.successful_steps,
        "replay_duration_s": replay_result.replay_duration_s,
        "steps":            steps,
    }


def _print_summary(stats: Dict[str, Any]) -> None:
    width = 60
    print("\n" + "═" * width)
    print("  COLLECTION SUMMARY")
    print("═" * width)
    total = stats["tasks_attempted"]
    rep   = stats["tasks_replayed"]
    ann   = stats["tasks_annotated"]
    sav   = stats["tasks_saved"]
    fail  = stats["tasks_failed"]
    dur   = stats.get("total_duration_s", 0)
    print(f"  Tasks attempted : {total}")
    print(f"  Replayed        : {rep}  ({rep/max(1,total):.0%})")
    print(f"  Annotated       : {ann}  ({ann/max(1,total):.0%})")
    print(f"  Saved           : {sav}  ({sav/max(1,total):.0%})")
    print(f"  Failed / skipped: {fail}")
    print(f"  Duration        : {dur:.1f}s  ({dur/max(1,total):.1f}s / task)")
    if stats["output_paths"]:
        print(f"  Output files:")
        for p in stats["output_paths"]:
            print(f"    {p}")
    print("═" * width + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  CLI entry-point
# ═══════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the failure-aware trajectory data collection pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--source", default="mind2web",
                   choices=["mind2web", "miniwob", "webarena", "all"],
                   help="Task dataset source")
    p.add_argument("--limit", type=int, default=20,
                   help="Maximum number of tasks to collect")
    p.add_argument("--output-dir", default="dataset",
                   help="Root output directory")
    p.add_argument("--no-headless", action="store_true",
                   help="Show browser window (useful for debugging)")
    p.add_argument("--step-delay", type=int, default=500,
                   help="Milliseconds to pause between actions")
    p.add_argument("--timeout", type=int, default=30_000,
                   help="Action timeout in milliseconds")
    p.add_argument("--miniwob-port", type=int, default=7860,
                   help="Port for local MiniWoB++ server")
    p.add_argument("--debug", action="store_true",
                   help="Enable DEBUG-level logging")
    return p.parse_args()


if __name__ == "__main__":
    # Force UTF-8 stdout/stderr on Windows (cp1252 can't render Rich Unicode)
    import sys, io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _parse_args()
    runner = CollectionRunner(
        output_dir    = args.output_dir,
        headless      = not args.no_headless,
        step_delay_ms = args.step_delay,
        timeout_ms    = args.timeout,
        miniwob_port  = args.miniwob_port,
        debug         = args.debug,
    )
    runner.run(source=args.source, limit=args.limit)
