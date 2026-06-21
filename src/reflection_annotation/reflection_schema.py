"""
Reflection Schema

Data models for reflection annotations including confidence scores,
reflection texts, and memory signals.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Type of memory update signal.
    
    Indicates what kind of experience should be stored for future learning.
    """
    
    SUCCESS = "success"  # Effective action pattern
    FAILURE = "failure"  # Known error pattern
    RECOVERY = "recovery"  # Working recovery strategy
    INSIGHT = "insight"  # New learning signal
    NONE = "none"  # No memory update needed


class ReasoningType(str, Enum):
    """Type of reasoning being performed.
    
    Categorizes the cognitive process used in the action.
    """
    
    DIAGNOSIS = "diagnosis"  # Identifying problems
    PLANNING = "planning"  # Choosing actions
    EXECUTION = "execution"  # Performing actions
    EVALUATION = "evaluation"  # Assessing outcomes
    RECOVERY = "recovery"  # Handling failures
    EXPLORATION = "exploration"  # Trying new approaches


class UncertaintySource(str, Enum):
    """Source of uncertainty in the action.
    
    Identifies why the agent is unsure about the outcome.
    """
    
    ELEMENT_DETECTION = "element_detection"  # Can't find target element
    ACTION_EFFECT = "action_effect"  # Unclear if action worked
    PAGE_STATE = "page_state"  # Page state ambiguous
    GOAL_ALIGNMENT = "goal_alignment"  # Unsure if advancing goal
    TIMING = "timing"  # Timing/synchronization issues
    SELECTOR_ACCURACY = "selector_accuracy"  # Wrong element selected
    NONE = "none"  # No significant uncertainty


class IntrospectionMetadata(BaseModel):
    """Additional introspection metadata.
    
    Captures the agent's internal reasoning and uncertainty.
    """
    
    reasoning_type: ReasoningType = Field(
        description="Type of reasoning being performed"
    )
    
    uncertainty_source: UncertaintySource = Field(
        default=UncertaintySource.NONE,
        description="Primary source of uncertainty"
    )
    
    learning_signal: str = Field(
        default="",
        description="Signal for future learning (e.g., 'improve_selector_strategy')"
    )
    
    alternative_hypotheses: List[str] = Field(
        default_factory=list,
        description="Alternative interpretations of the outcome"
    )
    
    context_factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual factors affecting reasoning"
    )


class ReflectionAnnotation(BaseModel):
    """Complete reflection annotation for a step.
    
    Contains all introspective information about an action and its outcome.
    """
    
    step_id: int = Field(
        ge=0,
        description="ID of the step being annotated"
    )
    
    # Confidence scores
    agent_confidence_before: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent's confidence before executing action (0.0-1.0)"
    )
    
    agent_confidence_after: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent's confidence after observing outcome (0.0-1.0)"
    )
    
    confidence_delta: float = Field(
        ge=-1.0,
        le=1.0,
        description="Change in confidence (after - before)"
    )
    
    # Reflection text
    reflection_text: str = Field(
        description="Natural language explanation of action and outcome"
    )
    
    # Memory signals
    memory_update_flag: bool = Field(
        default=False,
        description="Whether this experience should update agent memory"
    )
    
    memory_type: MemoryType = Field(
        default=MemoryType.NONE,
        description="Type of memory update (if flagged)"
    )
    
    # Introspection
    introspection_metadata: IntrospectionMetadata = Field(
        description="Additional introspection details"
    )
    
    # Calibration
    confidence_calibration: Optional[float] = Field(
        default=None,
        description="Calibration error if actual outcome known"
    )
    
    @property
    def is_confident(self) -> bool:
        """Check if agent was confident before action."""
        return self.agent_confidence_before >= 0.7
    
    @property
    def confidence_dropped(self) -> bool:
        """Check if confidence dropped after action."""
        return self.confidence_delta < -0.2
    
    @property
    def confidence_improved(self) -> bool:
        """Check if confidence improved after action."""
        return self.confidence_delta > 0.2


class ConfidenceCalibration(BaseModel):
    """Tracks confidence calibration over time.
    
    Used to tune confidence estimation based on actual outcomes.
    """
    
    predicted_success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Average predicted confidence"
    )
    
    actual_success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Actual success rate"
    )
    
    calibration_error: float = Field(
        ge=0.0,
        description="Absolute difference between predicted and actual"
    )
    
    samples: int = Field(
        ge=0,
        description="Number of samples used for calibration"
    )
    
    confidence_bins: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Binned calibration data (e.g., '0.8-0.9': {predicted: 0.85, actual: 0.78})"
    )
    
    @property
    def is_well_calibrated(self) -> bool:
        """Check if confidence is well calibrated (<15% error)."""
        return self.calibration_error < 0.15
    
    @property
    def is_overconfident(self) -> bool:
        """Check if predictions are overconfident."""
        return self.predicted_success_rate > self.actual_success_rate + 0.1
    
    @property
    def is_underconfident(self) -> bool:
        """Check if predictions are underconfident."""
        return self.predicted_success_rate < self.actual_success_rate - 0.1


class ReflectionConfig(BaseModel):
    """Configuration for reflection annotation.
    
    Controls confidence estimation, reflection generation, and memory signals.
    """
    
    # Confidence estimation
    base_confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Base confidence level before adjustments"
    )
    
    element_not_found_penalty: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Confidence reduction for element not found"
    )
    
    recent_failure_penalty: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Confidence reduction for recent failures"
    )
    
    high_complexity_penalty: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Confidence reduction for complex pages"
    )
    
    # Reflection generation
    include_metrics: bool = Field(
        default=True,
        description="Include metric values in reflection text"
    )
    
    max_reflection_length: int = Field(
        default=200,
        ge=50,
        le=500,
        description="Maximum characters in reflection text"
    )
    
    # Memory signals
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for certain decisions"
    )
    
    min_confidence_for_certainty: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence level to be considered certain"
    )
    
    high_confidence_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Threshold for high confidence"
    )
    
    uncertainty_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence delta to be considered uncertain"
    )
    
    memory_update_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence delta to trigger memory update"
    )
    
    novel_failure_threshold: int = Field(
        default=1,
        ge=1,
        description="Count threshold for novel failure detection"
    )
    
    # Calibration
    calibration_window: int = Field(
        default=100,
        ge=10,
        description="Number of samples for rolling calibration"
    )
    
    recalibrate_interval: int = Field(
        default=50,
        ge=10,
        description="Steps between calibration updates"
    )


# Default configuration instance
DEFAULT_REFLECTION_CONFIG = ReflectionConfig()


def create_reflection_annotation(
    step_id: int,
    confidence_before: float,
    confidence_after: float,
    reflection_text: str,
    memory_update: bool = False,
    memory_type: MemoryType = MemoryType.NONE,
    reasoning_type: ReasoningType = ReasoningType.EXECUTION,
    uncertainty_source: UncertaintySource = UncertaintySource.NONE,
) -> ReflectionAnnotation:
    """Helper function to create a ReflectionAnnotation.
    
    Args:
        step_id: Step ID
        confidence_before: Confidence before action
        confidence_after: Confidence after action
        reflection_text: Reflection text
        memory_update: Whether to update memory
        memory_type: Type of memory update
        reasoning_type: Type of reasoning
        uncertainty_source: Source of uncertainty
        
    Returns:
        ReflectionAnnotation instance
    """
    return ReflectionAnnotation(
        step_id=step_id,
        agent_confidence_before=confidence_before,
        agent_confidence_after=confidence_after,
        confidence_delta=confidence_after - confidence_before,
        reflection_text=reflection_text,
        memory_update_flag=memory_update,
        memory_type=memory_type,
        introspection_metadata=IntrospectionMetadata(
            reasoning_type=reasoning_type,
            uncertainty_source=uncertainty_source,
        ),
    )
