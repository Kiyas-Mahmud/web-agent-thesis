"""Automatic browser-based gold dataset collector.

This module reuses the existing BrowserReplay pipeline, then converts recorded
real browser steps into leakage-aware GoldStep rows. It writes audit rows with
observed metadata; training exports are handled separately by GoldExporter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from browser_replay import ActionLog, BrowserReplay, LogParser, ReplayConfig
from failure_labeling.decision_tree import classify_step
from metric_computation import MetricComputer

from .gold_schema import GoldStep, build_gold_step, normalize_recovery


@dataclass
class GoldCollectionConfig:
    output_dir: str = "output/gold_dataset"
    headless: bool = True
    step_delay_ms: int = 500
    timeout_ms: int = 30_000
    screenshot_format: str = "png"
    screenshot_quality: int = 95
    max_steps: Optional[int] = None
    no_change_pixel_threshold: float = 0.01
    no_change_ssim_threshold: float = 0.99


class GoldCollector:
    """Collect gold rows from ActionLog tasks using real browser replay."""

    def __init__(self, config: Optional[GoldCollectionConfig] = None):
        self.config = config or GoldCollectionConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.output_dir / "gold_audit.jsonl"
        self.metric_computer = MetricComputer(output_dir=str(self.output_dir))

    def collect_file(self, log_path: str | Path) -> List[GoldStep]:
        logs = LogParser().load_file(Path(log_path))
        return self.collect_logs(logs)

    def collect_logs(self, logs: Iterable[ActionLog]) -> List[GoldStep]:
        replay = BrowserReplay(self._replay_config())
        collected: List[GoldStep] = []

        for log in logs:
            result = replay.replay_task(log)
            trajectory = self._load_trajectory(result.trajectory_file)
            if trajectory is None:
                trajectory = self._minimal_trajectory(log, result)

            steps = self._trajectory_to_gold_steps(trajectory, log)
            collected.extend(steps)
            self._append_audit_rows(steps)

        return collected

    def _replay_config(self) -> ReplayConfig:
        return ReplayConfig(
            headless=self.config.headless,
            timeout_ms=self.config.timeout_ms,
            step_delay_ms=self.config.step_delay_ms,
            screenshot_format=self.config.screenshot_format,
            screenshot_quality=self.config.screenshot_quality,
            max_steps=self.config.max_steps,
            output_dir=str(self.output_dir),
            save_jsonl=True,
            continue_on_step_error=True,
        )

    def _load_trajectory(self, path: Optional[str]) -> Optional[Dict[str, Any]]:
        if not path:
            return None
        trajectory_path = Path(path)
        if not trajectory_path.is_file():
            return None
        with trajectory_path.open("r", encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line:
                    return json.loads(line)
        return None

    def _minimal_trajectory(self, log: ActionLog, replay_result: Any) -> Dict[str, Any]:
        steps = []
        for step_result in replay_result.step_results:
            steps.append(
                {
                    "step_id": step_result.step_index,
                    "action": {
                        "action_type": step_result.action_type,
                        "target": step_result.target,
                    },
                    "result": {
                        "success": step_result.status.value == "success",
                        "error": step_result.error_message,
                        "execution_time_ms": step_result.execution_time_ms,
                    },
                    "screenshot_before": step_result.screenshot_before,
                    "screenshot_after": step_result.screenshot_after,
                    "url_before": step_result.url_before,
                    "url_after": step_result.url_after,
                }
            )
        return {
            "task_id": log.task_id,
            "task_description": log.task_description or "",
            "source": log.source or "custom",
            "metadata": log.metadata or {},
            "steps": steps,
        }

    def _trajectory_to_gold_steps(self, trajectory: Dict[str, Any], log: ActionLog) -> List[GoldStep]:
        task_id = trajectory.get("task_id") or log.task_id
        task_description = trajectory.get("task_description") or log.task_description or ""
        source = trajectory.get("source") or log.source or "custom"
        website_domain = self._domain_from_log(log)

        gold_steps: List[GoldStep] = []
        annotated_history: List[Dict[str, Any]] = []

        for index, step in enumerate(trajectory.get("steps", [])):
            action = step.get("action") or {}
            result = step.get("result") or {}

            metrics = self._compute_metrics(index, step, result)
            if metrics:
                step["metrics"] = metrics

            fine_failure = self._derive_fine_failure(step, annotated_history, task_description)
            outcome = "SUCCESS" if fine_failure == "none" else "FAILURE"
            recovery_strategy = self._recovery_for_failure(fine_failure)

            gold_step = build_gold_step(
                task_id=task_id,
                step_index=index,
                source=source,
                website_domain=website_domain,
                task_description=task_description,
                state_before=self._relative_path(step.get("screenshot_before")),
                state_after=self._relative_path(step.get("screenshot_after")),
                action_type=action.get("action_type"),
                action_target_desc=action.get("description") or action.get("target") or "",
                action_coordinates=action.get("coordinates"),
                action_target_bbox=action.get("bbox") or action.get("target_bbox"),
                url_before=step.get("url_before"),
                url_after=step.get("url_after"),
                page_status=result.get("page_status"),
                http_status=result.get("http_status"),
                error_message=self._step_error_message(step, fine_failure),
                pixel_diff=self._visual_value(metrics, "pixel_diff_score"),
                ssim=self._visual_value(metrics, "ssim_score"),
                outcome_label=outcome,
                failure_type_fine=fine_failure,
                recovery_strategy_observed=recovery_strategy,
                recovery_attempted=False,
                recovery_success_observed=None,
                metadata={
                    "auto_label_reason": self._auto_label_reason(step, fine_failure),
                    "signals": (step.get("failure") or {}).get("signals_fired", []),
                },
            )
            gold_steps.append(gold_step)
            annotated_history.append(step)

        return gold_steps

    def _compute_metrics(self, index: int, step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        before = step.get("screenshot_before")
        after = step.get("screenshot_after")
        if not before or not after:
            return {"visual": {}, "state_hash": {}, "performance": {}}
        try:
            metrics = self.metric_computer.compute_step_metrics(
                step_id=index,
                before_screenshot=before,
                after_screenshot=after,
                execution_time_ms=float(result.get("execution_time_ms") or 0.0),
            )
            return metrics.to_dict()
        except Exception as exc:  # noqa: BLE001 - audit should preserve failure reason.
            return {
                "visual": {},
                "state_hash": {},
                "performance": {"execution_time_ms": result.get("execution_time_ms") or 0.0},
                "metric_error": str(exc),
            }

    def _derive_fine_failure(
        self,
        step: Dict[str, Any],
        history: List[Dict[str, Any]],
        task_description: str,
    ) -> str:
        result = step.get("result") or {}
        action = step.get("action") or {}
        action_type = str(action.get("action_type") or "").upper()

        if result.get("success") is False:
            if result.get("is_error_page") or result.get("page_status") == "ERROR_PAGE":
                return "tool_failure"

            if action_type in {"CLICK", "TYPE", "SELECT", "HOVER"} and action.get("target"):
                return "perception_error"

            try:
                classification = classify_step(step, history=history, task_description=task_description)
                return classification.failure_type
            except Exception:
                return "unknown"

        return "none"

    def _recovery_for_failure(self, fine_failure: str) -> str:
        mapping = {
            "none": "NONE",
            "tool_failure": "RETRY",
            "state_no_change": "REPLAN",
            "loop_detected": "BACKTRACK",
            "perception_error": "ALTERNATIVE_TARGET",
            "action_mismatch": "BACKTRACK",
            "goal_misalignment": "REPLAN",
            "reasoning_error": "REPLAN",
            "unknown": "RETRY",
        }
        return normalize_recovery(mapping.get(fine_failure, "RETRY"))

    def _auto_label_reason(self, step: Dict[str, Any], fine_failure: str) -> str:
        if fine_failure == "none":
            return "Observed step marked successful by browser replay and visual checks."
        result = step.get("result") or {}
        if result.get("error"):
            return str(result.get("error"))
        metrics = step.get("metrics") or {}
        visual = metrics.get("visual") or {}
        if visual:
            return (
                f"Auto label from observed metrics: pixel_diff={visual.get('pixel_diff_score')}, "
                f"ssim={visual.get('ssim_score')}"
            )
        return "Auto label from observed browser replay result."

    def _step_error_message(self, step: Dict[str, Any], fine_failure: str) -> Optional[str]:
        result = step.get("result") or {}
        error = result.get("error") or result.get("navigation_error")
        if error:
            return str(error)
        if result.get("success") is False:
            action = step.get("action") or {}
            action_type = action.get("action_type") or "UNKNOWN"
            target = action.get("target") or action.get("description") or ""
            if fine_failure == "perception_error" and target:
                return f"{action_type} failed: target not found or not interactable ({target})"
            return f"{action_type} failed without stored browser exception"
        return None

    def _visual_value(self, metrics: Dict[str, Any], name: str) -> Optional[float]:
        value = (metrics.get("visual") or {}).get(name)
        return float(value) if value is not None else None

    def _relative_path(self, value: Any) -> str:
        if not value:
            return ""
        path = Path(str(value))
        try:
            return path.relative_to(self.output_dir).as_posix()
        except ValueError:
            text = str(path).replace("\\", "/")
            prefix = self.output_dir.as_posix().rstrip("/") + "/"
            if text.startswith(prefix):
                return text[len(prefix) :]
            return text

    def _domain_from_log(self, log: ActionLog) -> str:
        metadata = log.metadata or {}
        if metadata.get("domain"):
            return str(metadata["domain"])
        url = log.start_url or ""
        if "://" in url:
            return url.split("://", 1)[1].split("/", 1)[0].lower().removeprefix("www.")
        return url

    def _append_audit_rows(self, steps: List[GoldStep]) -> None:
        if not steps:
            return
        with self.audit_path.open("a", encoding="utf-8") as f:
            for step in steps:
                f.write(json.dumps(step.model_dump(), ensure_ascii=False) + "\n")
