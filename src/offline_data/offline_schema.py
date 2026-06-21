"""
Schema definitions for offline augmented dataset.

Defines data structures for loading pre-captured screenshots and annotations
from Multimodal Mind2Web, and augmented steps with injected failures.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from PIL import Image
import numpy as np


@dataclass
class OfflineStep:
    """
    A single step from Multimodal Mind2Web dataset.
    Contains pre-captured screenshots and annotations.
    """
    
    # Task metadata
    task_id: str
    website: str
    domain: str
    confirmed_task: str
    
    # Step identification
    step_number: int
    annotation_id: str
    
    # Action details
    action_type: str  # CLICK, TYPE, SELECT, HOVER, etc.
    action_target: str  # Target element description
    action_uid: str  # Unique ID of target element
    action_coords: Optional[tuple[int, int]] = None  # Click coordinates
    action_text: Optional[str] = None  # Text to type
    
    # State screenshots (pre-captured)
    state_before: Optional[Image.Image] = None  # PIL Image
    state_after: Optional[Image.Image] = None  # PIL Image
    
    # Bounding boxes
    target_bbox: Optional[Dict[str, float]] = None  # {x, y, width, height}
    candidate_bboxes: List[Dict[str, Any]] = field(default_factory=list)
    
    # URLs
    url_before: str = ""
    url_after: str = ""
    
    # Visual metrics (computed from screenshots)
    pixel_diff: Optional[float] = None
    ssim: Optional[float] = None
    
    # Validation
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class OfflineTrajectory:
    """
    A complete trajectory from Multimodal Mind2Web.
    Contains sequence of pre-captured steps.
    """
    
    # Task metadata
    task_id: str
    website: str
    domain: str
    confirmed_task: str
    
    # Steps
    steps: List[OfflineStep] = field(default_factory=list)
    
    # Trajectory metadata
    num_steps: int = 0
    is_complete: bool = False
    
    # Gold trajectory info
    gold_outcome: str = "SUCCESS"  # Original trajectory was successful
    
    # Data source
    source_dataset: str = "multimodal_mind2web"
    loaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        self.num_steps = len(self.steps)


@dataclass
class AugmentedStep:
    """
    An offline step with injected failure and synthetic recovery.
    Extends OfflineStep with failure injection metadata.
    """
    
    # Original offline step
    original_step: OfflineStep
    
    # Augmentation metadata
    is_augmented: bool = False
    injection_type: Optional[str] = None  # TARGET_MISSING, MISCLICK, WRONG_OPERATION, etc.
    
    # Injected modifications
    state_before_modified: Optional[Image.Image] = None
    state_after_modified: Optional[Image.Image] = None
    action_modified: Optional[Dict[str, Any]] = None
    bbox_modified: Optional[Dict[str, float]] = None
    
    # Failure labels
    failure_type: Optional[str] = None  # perception_error, action_mismatch, reasoning_error, etc.
    failure_subtype: Optional[str] = None  # ELEMENT_MISSING, WRONG_COORDINATES, etc.
    failure_confidence: float = 0.0
    root_cause: Optional[str] = None
    
    # Recovery labels
    recovery_strategy: Optional[str] = None  # RETRY, BACKTRACK, ALTERNATIVE_TARGET, etc.
    recovery_action: Optional[Dict[str, Any]] = None
    recovery_success: bool = False
    recovery_duration_ms: int = 0
    
    # Visual metrics (after injection)
    pixel_diff_modified: Optional[float] = None
    ssim_modified: Optional[float] = None
    
    # Execution outcome
    execution_outcome: str = "SUCCESS"  # SUCCESS, FAILURE, PARTIAL
    
    # Provenance
    injection_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    injection_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AugmentedTrajectory:
    """
    An offline trajectory with injected failures and synthetic recoveries.
    """
    
    # Original trajectory
    original_trajectory: OfflineTrajectory
    
    # Augmented steps
    augmented_steps: List[AugmentedStep] = field(default_factory=list)
    
    # Trajectory-level statistics
    num_clean_steps: int = 0
    num_injected_failures: int = 0
    num_recoveries_attempted: int = 0
    num_recoveries_successful: int = 0
    
    # Failure type distribution
    failure_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Augmentation metadata
    injection_probability: float = 0.0
    target_distribution: Dict[str, float] = field(default_factory=dict)
    
    # Quality metrics
    dataset_balance_score: float = 0.0  # 0-1, how well it matches target distribution
    
    # Provenance
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self._compute_statistics()
    
    def _compute_statistics(self):
        """Compute trajectory-level statistics from augmented steps."""
        self.num_clean_steps = sum(1 for s in self.augmented_steps if not s.is_augmented)
        self.num_injected_failures = sum(1 for s in self.augmented_steps if s.is_augmented)
        self.num_recoveries_attempted = sum(
            1 for s in self.augmented_steps 
            if s.is_augmented and s.recovery_strategy is not None
        )
        self.num_recoveries_successful = sum(
            1 for s in self.augmented_steps 
            if s.is_augmented and s.recovery_success
        )
        
        # Failure distribution
        self.failure_distribution = {}
        for step in self.augmented_steps:
            if step.is_augmented and step.failure_type:
                self.failure_distribution[step.failure_type] = (
                    self.failure_distribution.get(step.failure_type, 0) + 1
                )
