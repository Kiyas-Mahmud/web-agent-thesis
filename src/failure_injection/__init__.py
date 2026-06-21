"""
Failure injection module for offline augmentation.

Provides systematic failure injection mechanisms:
- TARGET_MISSING: Mask element or remove bbox
- MISCLICK: Shift click coordinates
- WRONG_OPERATION: Swap action types
- NO_STATE_CHANGE: Duplicate state_before as state_after
- LOOP: Repeat same state multiple times
"""

from .injection_engine import (
    InjectionConfig,
    FailureInjector,
    InjectionPipeline,
)

from .target_missing import TargetMissingInjector
from .misclick import MisclickInjector
from .wrong_operation import WrongOperationInjector
from .no_state_change import NoStateChangeInjector
from .loop import LoopInjector

__all__ = [
    "InjectionConfig",
    "FailureInjector",
    "InjectionPipeline",
    "TargetMissingInjector",
    "MisclickInjector",
    "WrongOperationInjector",
    "NoStateChangeInjector",
    "LoopInjector",
]
