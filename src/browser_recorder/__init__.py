"""
Browser Recorder Module

This module handles browser automation, action execution, and trajectory recording.
"""

from .action_schema import (
    Action,
    ActionType,
    ActionResult,
    Step,
    Trajectory
)
from .browser_recorder import BrowserRecorder
from .session_manager import SessionManager
from .screenshot_capture import ScreenshotCapture

__all__ = [
    'Action',
    'ActionType',
    'ActionResult',
    'Step',
    'Trajectory',
    'BrowserRecorder',
    'SessionManager',
    'ScreenshotCapture',
]
