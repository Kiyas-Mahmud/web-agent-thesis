"""
Monitoring Schema
=================
Pydantic models shared across all monitoring components.

Covers:
- Structured log events
- Per-task and per-run counters
- Run manifest (reproducibility)
- Alert thresholds and events
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOG EVENTS
# ─────────────────────────────────────────────────────────────────────────────

class LogLevel(str, Enum):
    DEBUG   = "DEBUG"
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"


class LogEvent(BaseModel):
    """One structured log entry written to JSONL log files."""
    timestamp:  str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level:      LogLevel       = LogLevel.INFO
    component:  str            = "system"
    task_id:    Optional[str]  = None
    step_id:    Optional[int]  = None
    message:    str            = ""
    metadata:   Dict[str, Any] = Field(default_factory=dict)
    exception:  Optional[str]  = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. TASK / STEP RECORDS  (written per task to JSONL)
# ─────────────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    RUNNING  = "running"
    SUCCESS  = "success"
    PARTIAL  = "partial"
    FAILED   = "failed"
    SKIPPED  = "skipped"


class StepRecord(BaseModel):
    """Compact record for one replayed step."""
    step_index:       int
    action_type:      str
    target:           Optional[str]  = None
    success:          bool           = True
    execution_time_ms: float         = 0.0
    failure_type:     Optional[str]  = None
    error_message:    Optional[str]  = None


class TaskRecord(BaseModel):
    """Full record for one task run — appended to the run JSONL."""
    task_id:          str
    source:           str            = "custom"
    status:           TaskStatus     = TaskStatus.RUNNING
    start_time:       str            = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time:         Optional[str]  = None
    duration_s:       float          = 0.0
    total_steps:      int            = 0
    successful_steps: int            = 0
    failed_steps:     int            = 0
    steps:            List[StepRecord] = Field(default_factory=list)
    error_message:    Optional[str]  = None


# ─────────────────────────────────────────────────────────────────────────────
# 3. AGGREGATE COUNTERS  (in-memory, updated continuously)
# ─────────────────────────────────────────────────────────────────────────────

class RunCounters(BaseModel):
    """Live counters updated after every task/step."""
    tasks_processed:      int   = 0
    tasks_succeeded:      int   = 0
    tasks_partial:        int   = 0
    tasks_failed:         int   = 0
    steps_executed:       int   = 0
    step_failures:        int   = 0
    recoveries_attempted: int   = 0
    recoveries_succeeded: int   = 0
    total_duration_s:     float = 0.0

    # Computed properties
    @property
    def failure_rate(self) -> float:
        """Fraction of tasks that were failed or partial."""
        if self.tasks_processed == 0:
            return 0.0
        return (self.tasks_failed + self.tasks_partial) / self.tasks_processed

    @property
    def recovery_rate(self) -> float:
        if self.recoveries_attempted == 0:
            return 0.0
        return self.recoveries_succeeded / self.recoveries_attempted

    @property
    def tasks_per_hour(self) -> float:
        if self.total_duration_s < 1:
            return 0.0
        return self.tasks_processed / (self.total_duration_s / 3600)

    @property
    def step_failure_rate(self) -> float:
        if self.steps_executed == 0:
            return 0.0
        return self.step_failures / self.steps_executed


# ─────────────────────────────────────────────────────────────────────────────
# 4. RUN MANIFEST  (reproducibility snapshot)
# ─────────────────────────────────────────────────────────────────────────────

class EnvironmentInfo(BaseModel):
    python_version:  str                = ""
    platform:        str                = ""
    packages:        Dict[str, str]     = Field(default_factory=dict)   # name → version
    hardware:        Dict[str, Any]     = Field(default_factory=dict)
    env_variables:   Dict[str, str]     = Field(default_factory=dict)   # safe subset


class RunManifest(BaseModel):
    """Snapshot captured at run start and updated at run end."""
    run_id:      str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    start_time:  str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time:    Optional[str]         = None
    git_commit:  Optional[str]         = None
    git_branch:  Optional[str]         = None
    config:      Dict[str, Any]        = Field(default_factory=dict)
    environment: EnvironmentInfo       = Field(default_factory=EnvironmentInfo)
    results:     Optional[RunCounters] = None


# ─────────────────────────────────────────────────────────────────────────────
# 5. ALERTS
# ─────────────────────────────────────────────────────────────────────────────

class AlertLevel(str, Enum):
    INFO    = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertThresholds(BaseModel):
    """Configurable alert thresholds."""
    failure_rate_high:    float = 0.60   # > 60 % task failure → CRITICAL
    failure_rate_low:     float = 0.10   # < 10 % — suspiciously low
    recovery_rate_low:    float = 0.30   # < 30 % recovery success → WARNING
    storage_warning_gb:   float = 80.0   # dataset dir > 80 GB → WARNING
    storage_critical_gb:  float = 120.0  # > 120 GB → CRITICAL
    error_rate_high:      float = 0.10   # > 10 % step errors → WARNING
    task_timeout_s:       float = 300.0  # single task > 5 min → WARNING
    min_tasks_before_alert: int = 20     # don't alert until at least N tasks done


class AlertEvent(BaseModel):
    """One triggered alert."""
    timestamp:     str       = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level:         AlertLevel
    alert_type:    str       # e.g. "FAILURE_RATE_HIGH"
    message:       str
    current_value: float
    threshold:     float
