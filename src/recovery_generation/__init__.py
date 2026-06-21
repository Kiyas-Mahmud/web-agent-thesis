"""
Recovery Generation Module

This module provides automated recovery strategy generation and execution for
failed web interactions. When a failure is detected, the system selects and
executes appropriate recovery strategies to overcome the failure.

Key Components:
- RecoveryStrategy: Enum of 5 recovery strategies
- RecoveryResult: Outcome of recovery attempt
- RecoveryEngine: Main orchestration class for recovery
- StrategySelector: Maps failures to recovery strategies
- RecoveryExecutor: Executes recovery actions

Usage:
    from recovery_generation import RecoveryEngine
    
    engine = RecoveryEngine()
    recovery_result = engine.attempt_recovery(failure_label, context)
"""

from .recovery_schema import (
    RecoveryStrategy,
    RecoveryOutcome,
    RecoveryAction,
    RecoveryResult,
    RecoveryAttempt,
    RecoveryConfig,
    DEFAULT_RECOVERY_CONFIG,
)

from .strategy_selector import (
    StrategySelector,
    StrategyMapping,
)

from .recovery_executor import (
    RecoveryExecutor,
    RetryExecutor,
    BacktrackExecutor,
    AlternativeTargetExecutor,
    ReplanExecutor,
    AbortExecutor,
)

from .recovery_engine import (
    RecoveryEngine,
)

__all__ = [
    # Enums and schemas
    "RecoveryStrategy",
    "RecoveryOutcome",
    "RecoveryAction",
    "RecoveryResult",
    "RecoveryAttempt",
    "RecoveryConfig",
    "DEFAULT_RECOVERY_CONFIG",
    
    # Strategy selection
    "StrategySelector",
    "StrategyMapping",
    
    # Execution
    "RecoveryExecutor",
    "RetryExecutor",
    "BacktrackExecutor",
    "AlternativeTargetExecutor",
    "ReplanExecutor",
    "AbortExecutor",
    
    # Main interface
    "RecoveryEngine",
]
