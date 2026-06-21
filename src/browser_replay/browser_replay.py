"""
Browser Replay Engine

Replays an action log inside a real browser and captures before/after
screenshots at each step, producing a vision trajectory.

Architecture
────────────

  ActionLog  ──►  LogParser  ──►  [Action, Action, ...]
                                          │
                                          ▼
              BrowserRecorder.start_session(task_id, start_url)
                    │
                    ├── for each action:
                    │       record_step(action)
                    │           ├── screenshot_before
                    │           ├── execute action in Playwright
                    │           └── screenshot_after
                    │
                    └── end_session()  →  trajectory saved to records/

  BrowserRecorder.get_trajectory()  ──►  Trajectory (vision trajectory)
                                              └── saved as .jsonl

Usage
─────
    from browser_replay import BrowserReplay, ReplayConfig

    cfg = ReplayConfig(headless=True, output_dir="dataset")
    replay = BrowserReplay(cfg)

    result = replay.replay_file("logs/tasks.jsonl")
    print(f"Replayed {result.total_tasks} tasks, success rate {result.success_rate:.1%}")
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Module-level path fix so this works when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from browser_recorder import BrowserRecorder
from browser_recorder.action_schema import Action, ActionType

from .replay_schema import (
    ActionLog,
    ReplayConfig,
    ReplayStatus,
    StepReplayResult,
    StepReplayStatus,
    TaskReplayResult,
    BatchReplayResult,
)
from .log_parser import LogParser

logger = logging.getLogger(__name__)


class BrowserReplay:
    """
    Replay an action log in a real browser and produce a vision trajectory.

    Each call to replay_task() / replay_file() / replay_logs() is
    self-contained: it opens a fresh browser, executes every action,
    captures screenshots, and writes a JSONL trajectory file.

    Parameters
    ──────────
    config : ReplayConfig
        Replay configuration (headless mode, output directory, timeouts, …).
    """

    def __init__(self, config: Optional[ReplayConfig] = None):
        self.config = config or ReplayConfig()
        self.parser = LogParser()
        self._output_dir = Path(self.config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────

    def replay_file(self, log_path: Union[str, Path]) -> BatchReplayResult:
        """
        Replay all tasks in a log file (JSON or JSONL).

        Parameters
        ──────────
        log_path : path to the input log file

        Returns
        ───────
        BatchReplayResult with per-task details and aggregate stats
        """
        log_path = Path(log_path)
        logs = self.parser.load_file(log_path)
        return self.replay_logs(logs)

    def replay_logs(self, logs: List[ActionLog]) -> BatchReplayResult:
        """
        Replay a pre-parsed list of ActionLog objects.

        Returns
        ───────
        BatchReplayResult
        """
        batch = BatchReplayResult(
            total_tasks=len(logs),
            output_directory=str(self._output_dir),
        )
        t0 = time.time()

        for i, log in enumerate(logs, 1):
            print(f"\n[{i}/{len(logs)}] Replaying task: {log.task_id}")
            result = self.replay_task(log)
            batch.task_results.append(result)

            # Update batch counters
            if result.status == ReplayStatus.SUCCESS:
                batch.successful_tasks += 1
            elif result.status == ReplayStatus.PARTIAL:
                batch.partial_tasks += 1
            else:
                batch.failed_tasks += 1

            batch.total_steps += result.total_steps
            batch.total_screenshots += result.successful_steps * 2  # before + after

        batch.total_duration_s = time.time() - t0
        self._print_batch_summary(batch)
        return batch

    def replay_task(self, log: ActionLog) -> TaskReplayResult:
        """
        Replay a single ActionLog.  Blocks until replay is complete.

        Returns
        ───────
        TaskReplayResult with step-level detail and trajectory file path
        """
        return asyncio.run(self._replay_task_async(log))

    # ──────────────────────────────────────────────────────────
    # ASYNC CORE
    # ──────────────────────────────────────────────────────────

    async def _replay_task_async(self, log: ActionLog) -> TaskReplayResult:
        """Async implementation of replay_task."""
        t0 = time.time()

        result = TaskReplayResult(
            task_id=log.task_id,
            source=log.source or "custom",
            start_url=log.start_url,
            status=ReplayStatus.FAILED,
        )

        if not log.actions:
            result.status = ReplayStatus.EMPTY
            result.error_message = "Log contains no actions"
            logger.warning(f"Task {log.task_id}: no actions to replay")
            return result

        # Build the BrowserRecorder (fresh instance per task)
        recorder = self._build_recorder()

        actions: List[Action] = self.parser.to_actions(log)
        if self.config.max_steps:
            actions = actions[: self.config.max_steps]

        print(f"  Start URL : {log.start_url}")
        print(f"  Actions   : {len(actions)}")
        print(f"  Output    : {self._output_dir}")
        print()

        try:
            # ── Open browser and navigate to start URL ────────
            ok = await recorder.start_session(log.task_id, log.start_url)
            if not ok:
                result.error_message = "start_session() returned False"
                return result

            # ── Replay each action ────────────────────────────
            step_results: List[StepReplayResult] = []
            for idx, action in enumerate(actions):
                step_res = await self._replay_step(recorder, action, idx)
                step_results.append(step_res)

                symbol = "[OK]" if step_res.status == StepReplayStatus.SUCCESS else "[FAIL]"
                print(f"  {symbol} step {idx+1:02d}/{len(actions):02d}  "
                      f"{step_res.action_type:<12}  "
                      f"{(step_res.target or '')[:40]:<40}  "
                      f"{step_res.execution_time_ms:6.0f}ms")

                if step_res.status == StepReplayStatus.FAILED:
                    if not self.config.continue_on_step_error:
                        print(f"  Aborting replay: {step_res.error_message}")
                        break

                # Optional pause between steps
                if self.config.step_delay_ms > 0 and idx < len(actions) - 1:
                    await asyncio.sleep(self.config.step_delay_ms / 1000)

            # ── Get trajectory BEFORE end_session clears it ───
            trajectory = recorder.get_trajectory()

            # ── End session and save ──────────────────────────
            successful_count = sum(
                1 for s in step_results if s.status == StepReplayStatus.SUCCESS
            )
            await recorder.end_session(success=successful_count > 0)

            # ── Persist vision trajectory to JSONL ────────────
            trajectory_file: Optional[str] = None
            if trajectory and self.config.save_jsonl:
                trajectory_file = self._save_trajectory(trajectory, log)
                print(f"\n  Trajectory saved: {trajectory_file}")

            # ── Build result ──────────────────────────────────
            total = len(step_results)
            succ  = successful_count
            fail  = total - succ

            if fail == 0:
                status = ReplayStatus.SUCCESS
            elif succ > 0:
                status = ReplayStatus.PARTIAL
            else:
                status = ReplayStatus.FAILED

            result.status          = status
            result.total_steps     = total
            result.successful_steps = succ
            result.failed_steps    = fail
            result.step_results    = step_results
            result.trajectory_file = trajectory_file
            result.replay_duration_s = time.time() - t0

            print(f"\n  Status : {status.value.upper()}  |  "
                  f"Steps: {total}  |  OK: {succ}  |  Fail: {fail}  |  "
                  f"Time: {result.replay_duration_s:.1f}s")

        except Exception as exc:
            result.error_message = str(exc)
            result.status = ReplayStatus.FAILED
            logger.exception(f"Task {log.task_id}: replay aborted with error: {exc}")
            try:
                await recorder.end_session(success=False, error=str(exc))
            except Exception:
                pass

        return result

    async def _replay_step(
        self,
        recorder: BrowserRecorder,
        action: Action,
        idx: int,
    ) -> StepReplayResult:
        """Execute one action and return a StepReplayResult."""
        step_res = StepReplayResult(
            step_index=idx,
            action_type=str(action.action_type),
            target=action.target,
            status=StepReplayStatus.FAILED,
        )

        try:
            recorded_step = await recorder.record_step(action)

            step_res.execution_time_ms = recorded_step.result.execution_time_ms
            step_res.screenshot_before = recorded_step.screenshot_before
            step_res.screenshot_after  = recorded_step.screenshot_after
            step_res.url_before        = recorded_step.url_before
            step_res.url_after         = recorded_step.url_after

            if recorded_step.result.success:
                step_res.status = StepReplayStatus.SUCCESS
            else:
                step_res.status = StepReplayStatus.FAILED
                step_res.error_message = recorded_step.result.error

        except Exception as exc:
            step_res.status = StepReplayStatus.FAILED
            step_res.error_message = str(exc)
            logger.warning(f"Step {idx} failed: {exc}")

        return step_res

    # ──────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────

    def _build_recorder(self) -> BrowserRecorder:
        """Create a fresh BrowserRecorder with the current config."""
        browser_cfg = {
            "browser": {
                "headless": self.config.headless,
                "viewport": {
                    "width":  self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                "timeout": self.config.timeout_ms,
            },
            "screenshots": {
                "format":  self.config.screenshot_format,
                "quality": self.config.screenshot_quality,
            },
        }
        return BrowserRecorder(
            config=browser_cfg,
            output_dir=str(self._output_dir),
        )

    def _save_trajectory(self, trajectory, log: ActionLog) -> str:
        """
        Save the vision trajectory as a JSONL file and return the path.

        The file is written to <output_dir>/replays/<task_id>.jsonl.
        Extra fields from the source log (task_description, source, metadata)
        are injected into the trajectory dict before saving.
        """
        replays_dir = self._output_dir / "replays"
        replays_dir.mkdir(parents=True, exist_ok=True)

        out_path = replays_dir / f"{log.task_id}.jsonl"

        traj_dict = trajectory.to_dict()

        # Enrich with log-level metadata
        traj_dict["task_description"] = log.task_description
        traj_dict["source"]           = log.source
        traj_dict["metadata"]         = log.metadata

        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(traj_dict, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        return str(out_path)

    @staticmethod
    def _print_batch_summary(batch: BatchReplayResult) -> None:
        print("\n" + "=" * 70)
        print("BATCH REPLAY SUMMARY")
        print("=" * 70)
        print(f"  Tasks      : {batch.total_tasks}")
        print(f"  Successful : {batch.successful_tasks}")
        print(f"  Partial    : {batch.partial_tasks}")
        print(f"  Failed     : {batch.failed_tasks}")
        print(f"  Success %  : {batch.success_rate:.1%}")
        print(f"  Total steps: {batch.total_steps}")
        print(f"  Screenshots: {batch.total_screenshots}")
        print(f"  Duration   : {batch.total_duration_s:.1f}s")
        print(f"  Output dir : {batch.output_directory}")
        print("=" * 70)
