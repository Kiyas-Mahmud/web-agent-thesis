"""
Failure Labeling Schema

Defines data models for failure detection, diagnosis, and categorization.
Includes 9 failure types based on error taxonomy for web interaction agents.

Failure Types:
1. PERCEPTION_ERROR: Element not found, selector mismatch
2. ACTION_MISMATCH: Wrong action executed vs intended
3. STATE_NO_CHANGE: Action produced no observable state change
4. LOOP_DETECTED: Agent repeating same actions/states
5. GOAL_MISALIGNMENT: Action doesn't advance toward goal
6. TOOL_FAILURE: Browser/tool exception or timeout
7. UI_VARIATION: Unexpected page changes (redirects, popups)
8. REASONING_ERROR: Logical mistakes in action planning
9. NONE: No failure detected (success)
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class FailureType(str, Enum):
    """Categories of failures in web interaction trajectories."""
    
    # Perception failures - can't find or access target element
    PERCEPTION_ERROR = "perception_error"
    
    # Action execution failures - wrong action performed
    ACTION_MISMATCH = "action_mismatch"
    
    # State transition failures - no observable change after action
    STATE_NO_CHANGE = "state_no_change"
    
    # Loop/repetition failures - stuck in repeated behavior
    LOOP_DETECTED = "loop_detected"
    
    # Goal alignment failures - action doesn't advance task
    GOAL_MISALIGNMENT = "goal_misalignment"
    
    # Technical/tool failures - browser exceptions, timeouts
    TOOL_FAILURE = "tool_failure"
    
    # UI/environment failures - unexpected page behavior
    UI_VARIATION = "ui_variation"
    
    # Planning/reasoning failures - logical mistakes
    REASONING_ERROR = "reasoning_error"
    
    # No failure - successful execution
    NONE = "none"


class ExecutionOutcome(str, Enum):
    """Overall outcome of a step or trajectory."""
    
    SUCCESS = "success"           # Step executed successfully
    FAILURE = "failure"           # Step failed to execute
    PARTIAL_SUCCESS = "partial"   # Step partially succeeded


class FailureEvidence(BaseModel):
    """Evidence supporting a failure diagnosis.
    
    Contains specific signals, metrics, and observations that indicate
    a particular type of failure occurred.
    """
    
    signal_type: str = Field(
        description="Type of signal (e.g., 'no_visual_change', 'exception', 'loop')"
    )
    
    source: str = Field(
        description="Source of evidence (e.g., 'visual_metrics', 'state_hash', 'action_log')"
    )
    
    value: Any = Field(
        description="Measured value or observation"
    )
    
    expected: Optional[Any] = Field(
        default=None,
        description="Expected value if applicable"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence that this evidence indicates failure (0.0-1.0)"
    )
    
    description: str = Field(
        description="Human-readable description of the evidence"
    )


class FailureLabel(BaseModel):
    """Complete failure diagnosis for a step.
    
    Includes failure type, confidence, supporting evidence, and
    human-readable explanation.
    """
    
    failure_type: FailureType = Field(
        description="Categorized failure type"
    )
    
    outcome: ExecutionOutcome = Field(
        description="Overall execution outcome"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in this failure diagnosis (0.0-1.0)"
    )
    
    evidence: List[FailureEvidence] = Field(
        default_factory=list,
        description="Supporting evidence for this diagnosis"
    )
    
    primary_signal: Optional[str] = Field(
        default=None,
        description="Primary signal that triggered failure detection"
    )
    
    explanation: str = Field(
        description="Human-readable explanation of the failure"
    )
    
    severity: Optional[str] = Field(
        default=None,
        description="Severity level: 'low', 'medium', 'high'"
    )
    
    recoverable: Optional[bool] = Field(
        default=None,
        description="Whether this failure is potentially recoverable"
    )
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        """Validate severity level."""
        if v is not None and v not in ['low', 'medium', 'high']:
            raise ValueError("Severity must be 'low', 'medium', or 'high'")
        return v


class LabeledStep(BaseModel):
    """A recorded step with failure label and diagnosis.
    
    Extends the basic Step model with failure labeling information.
    """
    
    step_number: int = Field(
        ge=0,
        description="Index of this step in the trajectory"
    )
    
    action_type: str = Field(
        description="Type of action attempted (click, type, scroll, etc.)"
    )
    
    action_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the action"
    )
    
    failure_label: FailureLabel = Field(
        description="Failure diagnosis for this step"
    )
    
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when step was executed"
    )
    
    execution_time_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Time taken to execute this step in milliseconds"
    )


class LabeledTrajectory(BaseModel):
    """A complete trajectory with failure labels for each step.
    
    Includes aggregate statistics about failures in the trajectory.
    """
    
    trajectory_id: str = Field(
        description="Unique identifier for this trajectory"
    )
    
    task_id: Optional[str] = Field(
        default=None,
        description="Identifier of the task this trajectory attempts"
    )
    
    steps: List[LabeledStep] = Field(
        default_factory=list,
        description="Sequence of labeled steps"
    )
    
    overall_outcome: ExecutionOutcome = Field(
        description="Overall outcome of the entire trajectory"
    )
    
    failure_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each failure type in trajectory"
    )
    
    total_steps: int = Field(
        ge=0,
        description="Total number of steps in trajectory"
    )
    
    failed_steps: int = Field(
        ge=0,
        description="Number of steps that failed"
    )
    
    success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Proportion of successful steps (0.0-1.0)"
    )
    
    first_failure_step: Optional[int] = Field(
        default=None,
        description="Step number where first failure occurred"
    )
    
    @field_validator('failed_steps')
    @classmethod
    def validate_failed_steps(cls, v: int, info) -> int:
        """Validate that failed_steps <= total_steps."""
        if 'total_steps' in info.data and v > info.data['total_steps']:
            raise ValueError("failed_steps cannot exceed total_steps")
        return v


class DiagnosticConfig(BaseModel):
    """Configuration for failure detection and diagnosis.
    
    Controls sensitivity thresholds, detection rules, and behavior.
    """
    
    # Visual change detection
    min_visual_change: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Minimum pixel diff to consider visual change (default: 1%)"
    )
    
    ssim_threshold: float = Field(
        default=0.95,
        ge=-1.0,
        le=1.0,
        description="SSIM threshold - above this is 'no change' (default: 0.95)"
    )
    
    # Loop detection
    enable_loop_detection: bool = Field(
        default=True,
        description="Whether to detect loops in state sequences"
    )
    
    loop_window_size: int = Field(
        default=10,
        ge=2,
        description="Number of recent steps to check for loops"
    )
    
    # Timeout thresholds
    action_timeout_ms: float = Field(
        default=30000.0,
        ge=0.0,
        description="Maximum time for action execution (default: 30s)"
    )
    
    step_timeout_ms: float = Field(
        default=60000.0,
        ge=0.0,
        description="Maximum time for entire step including waits (default: 60s)"
    )
    
    # Confidence scoring
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to label as failure (default: 0.5)"
    )
    
    require_multiple_signals: bool = Field(
        default=False,
        description="Whether to require multiple evidence signals for high confidence"
    )
    
    # Exception handling
    treat_exceptions_as_failure: bool = Field(
        default=True,
        description="Whether browser exceptions always indicate failure"
    )
    
    # Severity assignment
    assign_severity: bool = Field(
        default=True,
        description="Whether to assign severity levels to failures"
    )
    
    # Recoverability analysis
    analyze_recoverability: bool = Field(
        default=True,
        description="Whether to assess if failures are recoverable"
    )


# Default configuration instance
DEFAULT_DIAGNOSTIC_CONFIG = DiagnosticConfig()


def create_failure_label(
    failure_type: FailureType,
    outcome: ExecutionOutcome,
    confidence: float,
    explanation: str,
    evidence: Optional[List[FailureEvidence]] = None,
    primary_signal: Optional[str] = None,
) -> FailureLabel:
    """Helper function to create a FailureLabel.
    
    Args:
        failure_type: Type of failure
        outcome: Execution outcome
        confidence: Confidence in diagnosis (0.0-1.0)
        explanation: Human-readable explanation
        evidence: Optional list of supporting evidence
        primary_signal: Optional primary signal that triggered detection
        
    Returns:
        FailureLabel instance
    """
    return FailureLabel(
        failure_type=failure_type,
        outcome=outcome,
        confidence=confidence,
        evidence=evidence or [],
        primary_signal=primary_signal,
        explanation=explanation,
    )


def create_success_label(explanation: str = "Step executed successfully") -> FailureLabel:
    """Create a label for successful execution (no failure).
    
    Args:
        explanation: Optional custom explanation
        
    Returns:
        FailureLabel indicating success
    """
    return FailureLabel(
        failure_type=FailureType.NONE,
        outcome=ExecutionOutcome.SUCCESS,
        confidence=1.0,
        evidence=[],
        explanation=explanation,
        severity="low",
        recoverable=True,
    )
