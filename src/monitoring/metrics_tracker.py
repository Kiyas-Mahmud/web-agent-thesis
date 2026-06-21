"""
Metrics Tracker
===============
Thread-safe in-memory counter aggregation updated after every task and step.

Also persists a rolling JSONL file so metrics survive a crash.

Usage
-----
    from monitoring import MetricsTracker

    tracker = MetricsTracker(output_dir="dataset")
    tracker.task_started("task_001", source="mind2web")
    tracker.step_done("task_001", action_type="CLICK", success=True, ms=320)
    tracker.step_done("task_001", action_type="TYPE",  success=False, ms=80,
                      failure_type="element_not_found")
    tracker.task_finished("task_001", status="partial", duration_s=14.2)

    summary = tracker.summary()
    print(f"Failure rate: {summary.failure_rate:.1%}")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .monitor_schema import (
    RunCounters,
    StepRecord,
    TaskRecord,
    TaskStatus,
)

logger = logging.getLogger("dc.MetricsTracker")


class MetricsTracker:
    """
    Records per-task and per-step events, aggregates them into RunCounters,
    and optionally writes a rolling JSONL report to disk.

    Thread-safe via a reentrant lock.
    """

    def __init__(self, output_dir: str | Path = "dataset"):
        self._lock    = threading.RLock()
        self._counters = RunCounters()
        self._run_start: float = time.time()

        # active tasks (task_id → TaskRecord) while they are running
        self._active: Dict[str, TaskRecord] = {}

        # Completed task list (kept in memory, also written to disk)
        self._completed: List[TaskRecord] = []

        # Rolling JSONL on disk
        self._out_dir = Path(output_dir) / "logs"
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._metrics_file = self._out_dir / "metrics.jsonl"

    # ─────────────────────────────────────────────────────────────────────
    # Task lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def task_started(self, task_id: str, source: str = "custom") -> None:
        with self._lock:
            self._active[task_id] = TaskRecord(
                task_id    = task_id,
                source     = source,
                status     = TaskStatus.RUNNING,
                start_time = datetime.utcnow().isoformat(),
            )
        logger.debug(f"task_started  {task_id}")

    def step_done(
        self,
        task_id:      str,
        action_type:  str,
        success:      bool,
        ms:           float          = 0.0,
        target:       Optional[str]  = None,
        failure_type: Optional[str]  = None,
        error_msg:    Optional[str]  = None,
        step_index:   int            = -1,
    ) -> None:
        with self._lock:
            rec = StepRecord(
                step_index        = step_index,
                action_type       = action_type,
                target            = target,
                success           = success,
                execution_time_ms = ms,
                failure_type      = failure_type,
                error_message     = error_msg,
            )

            # Update active task
            tr = self._active.get(task_id)
            if tr:
                tr.total_steps += 1
                if success:
                    tr.successful_steps += 1
                else:
                    tr.failed_steps  += 1
                tr.steps.append(rec)

            # Update global counters
            self._counters.steps_executed += 1
            if not success:
                self._counters.step_failures += 1

    def task_finished(
        self,
        task_id:    str,
        status:     str,    # "success" | "partial" | "failed" | "skipped"
        duration_s: float   = 0.0,
        error_msg:  Optional[str] = None,
        recoveries_attempted: int = 0,
        recoveries_succeeded: int = 0,
    ) -> None:
        with self._lock:
            tr = self._active.pop(task_id, None)
            if tr is None:
                # Task was never registered; create a minimal record
                tr = TaskRecord(task_id=task_id, source="unknown")

            ts = TaskStatus(status) if status in TaskStatus._value2member_map_ else TaskStatus.FAILED
            tr.status        = ts
            tr.end_time      = datetime.utcnow().isoformat()
            tr.duration_s    = duration_s
            tr.error_message = error_msg

            # Update aggregate counters
            self._counters.tasks_processed      += 1
            self._counters.recoveries_attempted += recoveries_attempted
            self._counters.recoveries_succeeded += recoveries_succeeded

            if ts == TaskStatus.SUCCESS:
                self._counters.tasks_succeeded += 1
            elif ts == TaskStatus.PARTIAL:
                self._counters.tasks_partial += 1
            elif ts == TaskStatus.FAILED:
                self._counters.tasks_failed += 1

            self._counters.total_duration_s = time.time() - self._run_start
            self._completed.append(tr)

            # Persist this task record
            self._append_to_file(tr)

        logger.debug(f"task_finished  {task_id}  {status}")

    # ─────────────────────────────────────────────────────────────────────
    # Accessor
    # ─────────────────────────────────────────────────────────────────────

    def summary(self) -> RunCounters:
        """Return a snapshot of current counters (thread-safe copy)."""
        with self._lock:
            self._counters.total_duration_s = time.time() - self._run_start
            return self._counters.model_copy()

    def active_tasks(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    def recent_completed(self, n: int = 5) -> List[TaskRecord]:
        with self._lock:
            return list(self._completed[-n:])

    # ─────────────────────────────────────────────────────────────────────
    # Storage metrics
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def dataset_size_gb(output_dir: str | Path) -> float:
        """Walk output_dir and return total size in GB."""
        total = 0
        for p in Path(output_dir).rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        return round(total / 1e9, 3)

    # ─────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────

    def _append_to_file(self, record: TaskRecord) -> None:
        try:
            with self._metrics_file.open("a", encoding="utf-8") as fh:
                fh.write(record.model_dump_json() + "\n")
        except Exception as exc:
            logger.warning(f"Could not write metrics file: {exc}")
