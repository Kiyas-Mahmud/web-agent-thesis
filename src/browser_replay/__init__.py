"""
Browser Replay Tool

Converts action logs into vision trajectories by replaying them
in a real Playwright browser and capturing before/after screenshots.

Quick start
───────────
    from browser_replay import BrowserReplay, ReplayConfig

    replay = BrowserReplay(ReplayConfig(headless=True, output_dir="dataset"))
    result = replay.replay_file("logs/tasks.jsonl")
"""

from .replay_schema import (
    ActionLog,
    LogAction,
    ReplayConfig,
    ReplayStatus,
    StepReplayStatus,
    StepReplayResult,
    TaskReplayResult,
    BatchReplayResult,
)
from .log_parser import LogParser
from .browser_replay import BrowserReplay

__all__ = [
    # Schema
    "ActionLog",
    "LogAction",
    "ReplayConfig",
    "ReplayStatus",
    "StepReplayStatus",
    "StepReplayResult",
    "TaskReplayResult",
    "BatchReplayResult",
    # Parser
    "LogParser",
    # Engine
    "BrowserReplay",
]
