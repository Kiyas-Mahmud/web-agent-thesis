"""
Structured Logger
=================
JSON-structured logging for the data-collection pipeline.

Features
--------
- Every log record is a JSON object on one line (JSONL)
- Main run log:  logs/run_<run_id>.jsonl
- Per-task log:  logs/tasks/<task_id>.jsonl
- Rotating file handler (10 MB, 5 backups)
- Console handler respects PYTHONLOGLEVEL / --debug flag
- Component tagging via get_logger(component_name)

Usage
-----
    from monitoring import get_logger

    log = get_logger("BrowserReplay")
    log.info("step_done", task_id="task_001", step_id=3, extra={"url": "..."})
    log.error("step_failed", task_id="task_001", step_id=3, exc_info=True)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .monitor_schema import LogEvent, LogLevel


# ─────────────────────────────────────────────────────────────────────────────
# JSON formatter
# ─────────────────────────────────────────────────────────────────────────────

class _JSONFormatter(logging.Formatter):
    """Formats every log record as a single JSON line."""

    def __init__(self, component: str = "system"):
        super().__init__()
        self._component = component

    def format(self, record: logging.LogRecord) -> str:            # noqa: A003
        exc_text: Optional[str] = None
        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info))

        # Pull structured extras set via log.info("msg", extra={...})
        metadata: dict[str, Any] = {}
        for key in vars(record):
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                metadata[key] = getattr(record, key)

        event = LogEvent(
            timestamp = datetime.utcfromtimestamp(record.created).isoformat(),
            level     = LogLevel(record.levelname) if record.levelname in LogLevel._value2member_map_ else LogLevel.INFO,
            component = getattr(record, "component", self._component),
            task_id   = getattr(record, "task_id",   None),
            step_id   = getattr(record, "step_id",   None),
            message   = record.getMessage(),
            metadata  = metadata,
            exception = exc_text,
        )
        return event.model_dump_json()


_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()
    | {"message", "asctime", "component", "task_id", "step_id"}
)


# ─────────────────────────────────────────────────────────────────────────────
# Console formatter (human-readable)
# ─────────────────────────────────────────────────────────────────────────────

class _ConsoleFormatter(logging.Formatter):
    _COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        color  = self._COLORS.get(record.levelname, "")
        task   = getattr(record, "task_id", None)
        tid    = f"  [{task}]" if task else ""
        ts     = datetime.utcfromtimestamp(record.created).strftime("%H:%M:%S")
        comp   = getattr(record, "component", record.name)
        return (
            f"{color}{ts}  {record.levelname:<8}{self._RESET}"
            f"  {comp:<28}{tid}  {record.getMessage()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Logger factory
# ─────────────────────────────────────────────────────────────────────────────

_run_id:   str  = "default"
_log_dir:  Path = Path("dataset/logs")
_debug:    bool = False

# Keep references so handlers can be closed cleanly
_run_file_handler: Optional[logging.handlers.RotatingFileHandler] = None


def configure_logging(
    run_id:   str,
    log_dir:  str | Path = "dataset/logs",
    debug:    bool       = False,
) -> None:
    """
    Call once at startup (CollectionRunner.__init__).

    Creates:
      - <log_dir>/run_<run_id>.jsonl   — all events, JSON
      - Console handler                — human-readable
    """
    global _run_id, _log_dir, _debug, _run_file_handler

    _run_id  = run_id
    _log_dir = Path(log_dir)
    _debug   = debug
    _log_dir.mkdir(parents=True, exist_ok=True)
    (_log_dir / "tasks").mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove any handlers added by previous configure_logging calls
    root.handlers.clear()

    # ── Run-level rotating JSONL file ──────────────────────────────────────
    run_log_path = _log_dir / f"run_{run_id}.jsonl"
    fh = logging.handlers.RotatingFileHandler(
        run_log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG if debug else logging.INFO)
    fh.setFormatter(_JSONFormatter("system"))
    root.addHandler(fh)
    _run_file_handler = fh

    # ── Console ────────────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    ch.setFormatter(_ConsoleFormatter())
    root.addHandler(ch)


# ─────────────────────────────────────────────────────────────────────────────
# Per-task file handler registry
# ─────────────────────────────────────────────────────────────────────────────

_task_handlers: dict[str, logging.handlers.RotatingFileHandler] = {}


def _ensure_task_handler(task_id: str) -> None:
    """Attach a per-task JSONL file handler to the root logger (once)."""
    if task_id in _task_handlers:
        return
    task_log = _log_dir / "tasks" / f"{task_id}.jsonl"
    th = logging.handlers.RotatingFileHandler(
        task_log, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
    )
    th.setLevel(logging.DEBUG)
    th.setFormatter(_JSONFormatter(task_id))
    logging.getLogger().addHandler(th)
    _task_handlers[task_id] = th


def close_task_handler(task_id: str) -> None:
    """Flush and detach the per-task handler when a task finishes."""
    handler = _task_handlers.pop(task_id, None)
    if handler:
        handler.flush()
        handler.close()
        logging.getLogger().removeHandler(handler)


# ─────────────────────────────────────────────────────────────────────────────
# Public helper: ComponentLogger
# ─────────────────────────────────────────────────────────────────────────────

class ComponentLogger:
    """
    Thin wrapper around stdlib logger that injects ``component`` and optional
    ``task_id`` / ``step_id`` into every record automatically.

    Usage
    -----
        log = get_logger("BrowserReplay")
        log.info("replaying", task_id="t001", step_id=3)
        log.error("action failed", task_id="t001", step_id=3, exc_info=True)
    """

    def __init__(self, component: str):
        self._component = component
        self._logger    = logging.getLogger(f"dc.{component}")

    def _extra(self, task_id: Optional[str], step_id: Optional[int]) -> dict:
        return {
            "component": self._component,
            **({"task_id": task_id} if task_id else {}),
            **({"step_id": step_id} if step_id is not None else {}),
        }

    def debug(self, msg: str, *, task_id: Optional[str] = None,
              step_id: Optional[int] = None, **kw: Any) -> None:
        self._logger.debug(msg, extra=self._extra(task_id, step_id), **kw)

    def info(self, msg: str, *, task_id: Optional[str] = None,
             step_id: Optional[int] = None, **kw: Any) -> None:
        self._logger.info(msg, extra=self._extra(task_id, step_id), **kw)

    def warning(self, msg: str, *, task_id: Optional[str] = None,
                step_id: Optional[int] = None, **kw: Any) -> None:
        self._logger.warning(msg, extra=self._extra(task_id, step_id), **kw)

    def error(self, msg: str, *, task_id: Optional[str] = None,
              step_id: Optional[int] = None, **kw: Any) -> None:
        self._logger.error(msg, extra=self._extra(task_id, step_id), **kw)

    def exception(self, msg: str, *, task_id: Optional[str] = None,
                  step_id: Optional[int] = None, **kw: Any) -> None:
        self._logger.exception(msg, extra=self._extra(task_id, step_id), **kw)

    # ── Task lifecycle helpers ─────────────────────────────────────────────
    def task_start(self, task_id: str, source: str, url: str) -> None:
        _ensure_task_handler(task_id)
        self.info(f"Task started  source={source}  url={url}", task_id=task_id)

    def task_end(self, task_id: str, status: str, steps: int, dur_s: float) -> None:
        self.info(
            f"Task finished  status={status}  steps={steps}  dur={dur_s:.1f}s",
            task_id=task_id,
        )
        close_task_handler(task_id)

    def step_done(self, task_id: str, step_id: int, action: str,
                  success: bool, ms: float) -> None:
        level = "DEBUG" if success else "WARNING"
        msg   = f"Step {'OK' if success else 'FAIL'}  action={action}  {ms:.0f}ms"
        getattr(self, level.lower())(msg, task_id=task_id, step_id=step_id)


def get_logger(component: str) -> ComponentLogger:
    """Return a ComponentLogger for the given component name."""
    return ComponentLogger(component)
