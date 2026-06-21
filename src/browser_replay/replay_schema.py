"""
Replay Schema

Data models for the Browser Replay Tool.
Defines input log format, replay configuration, and output result schema.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import time


# ─────────────────────────────────────────────
# 1. INPUT LOG FORMAT
# ─────────────────────────────────────────────

class LogAction(BaseModel):
    """
    A single action entry inside an input log file.

    This is the raw format that comes from external logs (Mind2Web, WebArena,
    custom annotation tools, etc.).  The log_parser converts these into the
    BrowserRecorder's Action objects before replay.
    """
    action_type: str = Field(..., description="Action type string e.g. 'CLICK', 'TYPE'")
    target: Optional[str] = Field(None, description="CSS selector or XPath")
    value: Optional[str] = Field(None, description="Input value for TYPE actions")
    key: Optional[str] = Field(None, description="Key name for PRESS_KEY actions")
    scroll_amount: Optional[int] = Field(None, description="Pixels for SCROLL")
    timeout: Optional[int] = Field(None, description="Override timeout in ms")
    coordinates: Optional[Dict[str, int]] = Field(None, description="x,y for coordinate-click")
    description: Optional[str] = Field(None, description="Human-readable step description")

    class Config:
        extra = "allow"                # Keep unknown fields from external sources


class ActionLog(BaseModel):
    """
    Complete input log for one task.

    A log file (JSON) must contain this structure.  Arrays of ActionLog are
    accepted as JSONL (one object per line).

    Example
    -------
    {
        "task_id": "mind2web_001",
        "start_url": "https://amazon.com",
        "task_description": "Search for 'laptop' and open the first result",
        "source": "mind2web",
        "actions": [
            {"action_type": "NAVIGATE", "value": "https://amazon.com"},
            {"action_type": "TYPE",     "target": "#twotabsearchtextbox", "value": "laptop"},
            {"action_type": "PRESS_KEY","key": "Enter"},
            {"action_type": "CLICK",    "target": ".s-result-item:first-child h2 a"}
        ]
    }
    """
    task_id: str = Field(..., description="Unique task identifier")
    start_url: str = Field(..., description="URL to navigate to before replaying")
    task_description: Optional[str] = Field(None, description="Natural language goal")
    source: Optional[str] = Field("custom", description="Dataset source (mind2web, webarena, …)")
    actions: List[LogAction] = Field(..., description="Ordered list of actions to replay")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        extra = "allow"


# ─────────────────────────────────────────────
# 2. REPLAY CONFIGURATION
# ─────────────────────────────────────────────

class ReplayConfig(BaseModel):
    """
    Configuration settings for the replay engine.
    """
    # Browser settings
    headless: bool = Field(True, description="Run browser in headless mode")
    viewport_width: int = Field(1280, description="Browser viewport width")
    viewport_height: int = Field(720, description="Browser viewport height")
    timeout_ms: int = Field(30_000, description="Default action timeout in ms")

    # Screenshot settings
    screenshot_format: str = Field("png", description="Screenshot format: png or jpeg")
    screenshot_quality: int = Field(95, description="JPEG quality (1-100)")

    # Replay behaviour
    step_delay_ms: int = Field(500, description="Pause between steps in ms")
    continue_on_step_error: bool = Field(True,  description="Continue replay when a step fails")
    max_steps: Optional[int] = Field(None, description="Cap on steps per task (None = no limit)")
    wait_for_load: bool = Field(True, description="Wait for page stability after each action")

    # Output
    output_dir: str = Field("dataset", description="Root output directory")
    save_jsonl: bool = Field(True, description="Persist trajectory to JSONL")


# ─────────────────────────────────────────────
# 3. REPLAY RESULT
# ─────────────────────────────────────────────

class StepReplayStatus(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    SKIPPED = "skipped"


class StepReplayResult(BaseModel):
    """Result for a single replayed step."""
    step_index: int
    action_type: str
    target: Optional[str] = None
    status: StepReplayStatus
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    url_before: Optional[str] = None
    url_after: Optional[str] = None


class ReplayStatus(str, Enum):
    SUCCESS        = "success"      # All steps completed
    PARTIAL        = "partial"      # Some steps failed, replay continued
    FAILED         = "failed"       # Fatal error, replay aborted
    EMPTY          = "empty"        # Log had no actions


class TaskReplayResult(BaseModel):
    """
    Full result for one replayed task.

    Contains per-step detail AND the path to the saved vision trajectory.
    """
    task_id: str
    source: str = "custom"
    start_url: str
    status: ReplayStatus

    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0

    replay_duration_s: float = 0.0
    step_results: List[StepReplayResult] = Field(default_factory=list)

    trajectory_file: Optional[str] = None   # Path to saved JSONL trajectory
    error_message: Optional[str] = None


class BatchReplayResult(BaseModel):
    """
    Aggregate result for replaying a batch of logs.
    """
    total_tasks: int = 0
    successful_tasks: int = 0
    partial_tasks: int = 0
    failed_tasks: int = 0
    total_steps: int = 0
    total_screenshots: int = 0
    total_duration_s: float = 0.0
    output_directory: str = ""
    task_results: List[TaskReplayResult] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
