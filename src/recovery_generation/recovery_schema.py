"""
Recovery Schema

Defines data models for recovery strategy generation and execution.
Includes 5 recovery strategies and comprehensive tracking of recovery attempts.

Recovery Strategies:
1. RETRY: Re-execute the same action (handles transient failures)
2. BACKTRACK: Revert to previous state and try different path
3. ALTERNATIVE_TARGET: Try different element with similar semantics
4. REPLAN: Generate new action sequence from current state
5. ABORT: Terminate gracefully (failure is unrecoverable)
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RecoveryStrategy(str, Enum):
    """Types of recovery strategies."""
    
    RETRY = "retry"                        # Re-execute same action
    BACKTRACK = "backtrack"                # Revert to previous state
    ALTERNATIVE_TARGET = "alternative_target"  # Try different element
    REPLAN = "replan"                      # Generate new action sequence
    ABORT = "abort"                        # Terminate gracefully


class RecoveryOutcome(str, Enum):
    """Outcome of a recovery attempt."""
    
    SUCCESS = "success"           # Recovery succeeded
    FAILURE = "failure"           # Recovery failed
    PARTIAL = "partial"           # Partially successful
    ABORTED = "aborted"           # Recovery was aborted


class RecoveryAction(BaseModel):
    """A single action within a recovery attempt.
    
    Represents one step in a potentially multi-step recovery process.
    """
    
    action_type: str = Field(
        description="Type of action (click, type, navigate, etc.)"
    )
    
    action_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the action"
    )
    
    expected_outcome: Optional[str] = Field(
        default=None,
        description="Expected outcome of this action"
    )
    
    timeout_ms: float = Field(
        default=30000,
        ge=0,
        description="Timeout for action execution in milliseconds"
    )


class RecoveryResult(BaseModel):
    """Result of a recovery attempt.
    
    Contains the outcome, actions taken, and metrics about the recovery.
    """
    
    strategy: RecoveryStrategy = Field(
        description="Recovery strategy used"
    )
    
    outcome: RecoveryOutcome = Field(
        description="Outcome of recovery attempt"
    )
    
    actions_taken: List[RecoveryAction] = Field(
        default_factory=list,
        description="Sequence of actions executed during recovery"
    )
    
    success: bool = Field(
        description="Whether recovery was successful"
    )
    
    duration_ms: float = Field(
        ge=0,
        description="Total duration of recovery attempt in milliseconds"
    )
    
    visual_change_detected: bool = Field(
        default=False,
        description="Whether visual state change was observed"
    )
    
    failure_repeated: bool = Field(
        default=False,
        description="Whether the same failure occurred again"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if recovery failed"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Confidence that recovery succeeded (0.0-1.0)"
    )


class RecoveryAttempt(BaseModel):
    """Complete record of a recovery attempt.
    
    Tracks a complete recovery workflow with potentially multiple strategies tried.
    """
    
    failure_type: str = Field(
        description="Type of failure that triggered recovery"
    )
    
    failure_severity: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Severity of the failure (0.0-1.0)"
    )
    
    recovery_results: List[RecoveryResult] = Field(
        default_factory=list,
        description="All recovery attempts made (multiple strategies may be tried)"
    )
    
    final_result: RecoveryResult = Field(
        description="Final outcome after all attempts"
    )
    
    success: bool = Field(
        description="Whether recovery ultimately succeeded"
    )
    
    total_duration_ms: float = Field(
        ge=0.0,
        description="Total time spent on all recovery attempts"
    )
    
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of recovery attempt"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (URL, element info, etc.)"
    )


class RecoveryConfig(BaseModel):
    """Configuration for recovery engine behavior.
    
    Controls retry limits, timeouts, and strategy selection parameters.
    """
    
    # Retry strategy parameters
    retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts"
    )
    
    retry_backoff_ms: float = Field(
        default=1000,
        ge=0,
        description="Backoff delay between retries in milliseconds"
    )
    
    # Backtrack strategy parameters
    backtrack_max_steps: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum steps to backtrack"
    )
    
    # Alternative target parameters
    alternative_max_candidates: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum alternative targets to try"
    )
    
    # Replan strategy parameters
    replan_max_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum replan attempts"
    )
    
    # General parameters
    max_total_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum total recovery attempts before giving up"
    )
    
    recovery_timeout_ms: float = Field(
        default=30000,
        ge=1000,
        description="Timeout for entire recovery attempt in milliseconds"
    )
    
    enable_multi_step_recovery: bool = Field(
        default=True,
        description="Whether to allow multi-step recovery attempts"
    )
    
    # Success evaluation thresholds
    min_visual_change: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Minimum visual change to consider recovery successful (10%)"
    )
    
    # Strategy selection
    allow_fallback_strategies: bool = Field(
        default=True,
        description="Whether to try secondary strategies if primary fails"
    )
    
    # Abort conditions
    abort_on_repeated_failure: bool = Field(
        default=True,
        description="Abort if same failure repeats after recovery"
    )
    
    max_recovery_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum nested recovery attempts"
    )


# Default configuration instance
DEFAULT_RECOVERY_CONFIG = RecoveryConfig()


def create_recovery_result(
    strategy: RecoveryStrategy,
    outcome: RecoveryOutcome,
    success: bool,
    duration_ms: float,
    actions: Optional[List[RecoveryAction]] = None,
    error_message: Optional[str] = None,
) -> RecoveryResult:
    """Helper function to create a RecoveryResult.
    
    Args:
        strategy: Recovery strategy used
        outcome: Outcome of recovery
        success: Whether recovery succeeded
        duration_ms: Duration in milliseconds
        actions: Optional list of actions taken
        error_message: Optional error message
        
    Returns:
        RecoveryResult instance
    """
    return RecoveryResult(
        strategy=strategy,
        outcome=outcome,
        actions_taken=actions or [],
        success=success,
        duration_ms=duration_ms,
        error_message=error_message,
        confidence=1.0 if success else 0.3,
    )


def create_abort_result(reason: str, duration_ms: float = 0.0) -> RecoveryResult:
    """Create a result for an aborted recovery.
    
    Args:
        reason: Reason for abort
        duration_ms: Duration before abort
        
    Returns:
        RecoveryResult indicating abort
    """
    return RecoveryResult(
        strategy=RecoveryStrategy.ABORT,
        outcome=RecoveryOutcome.ABORTED,
        actions_taken=[],
        success=False,
        duration_ms=duration_ms,
        error_message=reason,
        confidence=0.0,
    )
