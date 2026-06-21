"""
Task Loader Module

This module handles loading and normalizing tasks from multiple sources:
- Mind2Web (HuggingFace streaming)  — main backbone
- MiniWoB++  (local environment)    — controlled failure lab
- WebArena   (task configs only)    — long-horizon evaluation
"""

from .task_schema import (
    Task, 
    TaskMetadata, 
    TaskSource, 
    TaskDifficulty, 
    TaskCategory
)
from .task_loader import TaskLoader
from .parsers import Mind2WebParser, MiniWoBParser, WebArenaParser

__all__ = [
    'Task',
    'TaskMetadata',
    'TaskSource',
    'TaskDifficulty',
    'TaskCategory',
    'TaskLoader',
    'Mind2WebParser',
    'MiniWoBParser',
    'WebArenaParser',
]
