"""
Progress Dashboard
==================
Terminal progress display for the data-collection run.

Uses ``rich`` when available for a live updating table; falls back to
plain ANSI progress lines otherwise.

Usage
-----
    from monitoring import ProgressDashboard

    dash = ProgressDashboard(total_tasks=200, output_dir="dataset")
    dash.start()

    # after every task:
    dash.update(counters, recent_tasks)

    # at the end:
    dash.finish(counters)
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .monitor_schema import RunCounters, TaskRecord

# ─────────────────────────────────────────────────────────────────────────────
# Rich availability
# ─────────────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich import box as rich_box
    _RICH = True
except ImportError:
    _RICH = False


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bar(fraction: float, width: int = 20) -> str:
    filled = int(fraction * width)
    return "█" * filled + "░" * (width - filled)


def _eta(done: int, total: int, elapsed_s: float) -> str:
    if done == 0 or elapsed_s < 1:
        return "--:--"
    remaining = (total - done) * (elapsed_s / done)
    return str(timedelta(seconds=int(remaining)))


def _status_icon(status: str) -> str:
    return {"success": "✅", "partial": "⚠️ ", "failed": "❌", "running": "🔄",
            "skipped": "⏭ "}.get(status, "?")


# ─────────────────────────────────────────────────────────────────────────────
# Plain-text fallback dashboard
# ─────────────────────────────────────────────────────────────────────────────

class _PlainDashboard:
    def __init__(self, total_tasks: int, run_id: str):
        self._total   = total_tasks
        self._run_id  = run_id
        self._t0      = time.time()
        print(f"\n{'─'*60}")
        print(f"  Data Collection Monitor  |  run {run_id}")
        print(f"{'─'*60}")

    def update(self, counters: RunCounters, recent: List[TaskRecord]) -> None:
        done    = counters.tasks_processed
        frac    = done / max(self._total, 1)
        elapsed = time.time() - self._t0

        print(
            f"\r  [{_bar(frac, 30)}]  {done}/{self._total} tasks  "
            f"fail={counters.failure_rate:.0%}  "
            f"rec={counters.recovery_rate:.0%}  "
            f"ETA {_eta(done, self._total, elapsed)}",
            end="", flush=True
        )

    def finish(self, counters: RunCounters) -> None:
        elapsed = time.time() - self._t0
        print()
        print(f"\n{'─'*60}")
        print(f"  Run complete  {counters.tasks_processed} tasks  "
              f"elapsed {timedelta(seconds=int(elapsed))}")
        print(f"  Failure rate : {counters.failure_rate:.1%}")
        print(f"  Recovery rate: {counters.recovery_rate:.1%}")
        print(f"  Tasks/hour   : {counters.tasks_per_hour:.1f}")
        print(f"{'─'*60}\n")

    # stub
    def __enter__(self): return self
    def __exit__(self, *_): pass


# ─────────────────────────────────────────────────────────────────────────────
# Rich dashboard
# ─────────────────────────────────────────────────────────────────────────────

class _RichDashboard:
    def __init__(self, total_tasks: int, run_id: str):
        self._total  = total_tasks
        self._run_id = run_id
        self._t0     = time.time()
        self._console = Console()
        self._live: Optional[Live] = None

    def _make_table(
        self,
        counters: RunCounters,
        recent:   List[TaskRecord],
    ) -> Panel:
        elapsed = time.time() - self._t0
        done    = counters.tasks_processed

        # ── Stats table ───────────────────────────────────────────────
        tbl = Table(show_header=False, box=rich_box.SIMPLE, expand=True)
        tbl.add_column("K", style="bold cyan", width=24)
        tbl.add_column("V")

        bar_str = _bar(done / max(self._total, 1), 30)
        tbl.add_row("Progress",
                    f"[bold]{bar_str}[/bold]  {done}/{self._total}")
        tbl.add_row("Failure rate",
                    f"[{'red' if counters.failure_rate > 0.5 else 'green'}]"
                    f"{counters.failure_rate:.1%}[/]")
        tbl.add_row("Recovery rate",
                    f"[yellow]{counters.recovery_rate:.1%}[/]")
        tbl.add_row("Steps executed",  str(counters.steps_executed))
        tbl.add_row("Step error rate", f"{counters.step_failure_rate:.1%}")
        tbl.add_row("Tasks / hour",    f"{counters.tasks_per_hour:.1f}")
        tbl.add_row(
            "ETA",
            _eta(done, self._total, elapsed),
        )
        tbl.add_row(
            "Elapsed",
            str(timedelta(seconds=int(elapsed))),
        )

        # ── Recent tasks ──────────────────────────────────────────────
        if recent:
            tbl.add_row("", "")
            tbl.add_row("[bold]Recent tasks[/bold]", "")
            for tr in recent[-5:]:
                icon = _status_icon(tr.status.value)
                tbl.add_row(
                    f"  {tr.task_id[:28]}",
                    f"{icon} {tr.status.value}  {tr.total_steps} steps  "
                    f"{tr.duration_s:.1f}s",
                )

        return Panel(
            tbl,
            title=f"[bold]Data Collection Monitor[/bold]  run={self._run_id}",
            border_style="bright_blue",
        )

    def start(self) -> None:
        self._live = Live(console=self._console, refresh_per_second=2)
        self._live.__enter__()

    def update(self, counters: RunCounters, recent: List[TaskRecord]) -> None:
        if self._live:
            self._live.update(self._make_table(counters, recent))

    def finish(self, counters: RunCounters) -> None:
        if self._live:
            self._live.__exit__(None, None, None)
        elapsed = time.time() - self._t0
        self._console.print(f"\n[bold green]Run complete[/bold green]  "
                            f"{counters.tasks_processed} tasks  "
                            f"elapsed {timedelta(seconds=int(elapsed))}")
        self._console.print(f"  Failure rate : {counters.failure_rate:.1%}")
        self._console.print(f"  Recovery rate: {counters.recovery_rate:.1%}")
        self._console.print(f"  Tasks / hour : {counters.tasks_per_hour:.1f}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        pass   # finish() called explicitly


# ─────────────────────────────────────────────────────────────────────────────
# Public facade
# ─────────────────────────────────────────────────────────────────────────────

class ProgressDashboard:
    """
    Terminal dashboard.  Automatically uses Rich if installed,
    falls back to plain ANSI otherwise.

    Usage
    -----
        dash = ProgressDashboard(total_tasks=200, run_id="run_abc")
        dash.start()
        for task in tasks:
            ...run task...
            dash.update(tracker.summary(), tracker.recent_completed())
        dash.finish(tracker.summary())
    """

    def __init__(
        self,
        total_tasks: int,
        run_id:      str  = "run",
        output_dir:  str | Path = "dataset",
    ):
        self._total     = total_tasks
        self._output_dir = Path(output_dir)
        impl_cls = _RichDashboard if _RICH else _PlainDashboard
        self._impl = impl_cls(total_tasks=total_tasks, run_id=run_id)

    def start(self) -> None:
        if hasattr(self._impl, "start"):
            self._impl.start()

    def update(self, counters: RunCounters, recent: List[TaskRecord] = []) -> None:
        self._impl.update(counters, recent)

    def finish(self, counters: RunCounters) -> None:
        self._impl.finish(counters)
        self._write_daily_report(counters)

    # ── Daily text report ─────────────────────────────────────────────────

    def _write_daily_report(self, counters: RunCounters) -> None:
        today   = datetime.utcnow().strftime("%Y-%m-%d")
        reports = self._output_dir / "logs" / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        path    = reports / f"report_{today}.md"

        md = f"""# Daily Data Collection Report — {today}

## Summary

- Tasks completed : {counters.tasks_processed}
- Failure rate    : {counters.failure_rate:.1%}
- Recovery success: {counters.recovery_rate:.1%}
- Steps executed  : {counters.steps_executed}
- Step error rate : {counters.step_failure_rate:.1%}
- Tasks / hour    : {counters.tasks_per_hour:.1f}
- Total duration  : {timedelta(seconds=int(counters.total_duration_s))}

## Failure Breakdown

- Tasks succeeded : {counters.tasks_succeeded}
- Tasks partial   : {counters.tasks_partial}
- Tasks failed    : {counters.tasks_failed}

## Recovery

- Attempted : {counters.recoveries_attempted}
- Succeeded : {counters.recoveries_succeeded}

---
*Generated {datetime.utcnow().isoformat()}*
"""
        path.write_text(md, encoding="utf-8")
