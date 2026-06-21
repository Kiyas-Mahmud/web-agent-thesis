"""
Data Cleaning Schema

Data models for validation rules, split configuration, and statistics.
"""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """Valid action types."""
    
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SELECT = "select"
    NAVIGATE = "navigate"
    WAIT = "wait"
    PRESS_KEY = "press_key"
    CUSTOM = "custom"


class ValidationRule(BaseModel):
    """Validation rules for data cleaning.
    
    Defines required fields, valid values, and constraints.
    """
    
    required_fields: List[str] = Field(
        default_factory=lambda: [
            "task_id",
            "step_id",
            "action_type",
            "screenshot_before",
            "screenshot_after",
            "execution_outcome",
        ],
        description="Fields that must exist in each record"
    )
    
    valid_action_types: Set[str] = Field(
        default_factory=lambda: {t.value for t in ActionType},
        description="Allowed action types"
    )
    
    image_extensions: Set[str] = Field(
        default_factory=lambda: {".png", ".jpg", ".jpeg"},
        description="Valid image file extensions"
    )
    
    min_trajectory_length: int = Field(
        default=3,
        ge=1,
        description="Minimum number of steps in trajectory"
    )
    
    max_trajectory_length: int = Field(
        default=100,
        ge=1,
        description="Maximum number of steps in trajectory"
    )
    
    max_failure_rate: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Maximum allowed failure rate per trajectory"
    )
    
    require_images: bool = Field(
        default=True,
        description="Whether to check for image file existence"
    )


class SplitConfig(BaseModel):
    """Configuration for dataset splitting.
    
    Controls train/val/test split ratios and stratification.
    """
    
    train_ratio: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Proportion of data for training"
    )
    
    val_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Proportion of data for validation"
    )
    
    test_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Proportion of data for testing"
    )
    
    stratify_by: List[str] = Field(
        default_factory=lambda: ["domain", "failure_type"],
        description="Fields to stratify by"
    )
    
    min_samples_per_domain: int = Field(
        default=10,
        ge=1,
        description="Minimum samples required per domain"
    )
    
    ensure_recovery_pairs: bool = Field(
        default=True,
        description="Keep failure-recovery pairs in same split"
    )
    
    random_seed: int = Field(
        default=42,
        description="Random seed for reproducibility"
    )
    
    def __post_init__(self):
        """Validate that ratios sum to 1.0."""
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")


class ValidationResult(BaseModel):
    """Result of validation check."""
    
    record_id: str = Field(
        description="Identifier for the record"
    )
    
    is_valid: bool = Field(
        description="Whether record passed validation"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors encountered"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Validation warnings (non-fatal)"
    )


class CleaningResult(BaseModel):
    """Result of data cleaning operation."""
    
    total_records: int = Field(
        ge=0,
        description="Total number of input records"
    )
    
    valid_records: int = Field(
        ge=0,
        description="Number of valid records"
    )
    
    removed_duplicates: int = Field(
        default=0,
        ge=0,
        description="Number of duplicate records removed"
    )
    
    removed_incomplete: int = Field(
        default=0,
        ge=0,
        description="Number of incomplete records removed"
    )
    
    removed_invalid: int = Field(
        default=0,
        ge=0,
        description="Number of invalid records removed"
    )
    
    validation_results: List[ValidationResult] = Field(
        default_factory=list,
        description="Detailed validation results"
    )
    
    @property
    def total_removed(self) -> int:
        """Total number of removed records."""
        return (
            self.removed_duplicates
            + self.removed_incomplete
            + self.removed_invalid
        )
    
    @property
    def retention_rate(self) -> float:
        """Proportion of records retained."""
        if self.total_records == 0:
            return 0.0
        return self.valid_records / self.total_records


class SplitResult(BaseModel):
    """Result of dataset splitting."""
    
    train_ids: List[str] = Field(
        default_factory=list,
        description="Task IDs in training split"
    )
    
    val_ids: List[str] = Field(
        default_factory=list,
        description="Task IDs in validation split"
    )
    
    test_ids: List[str] = Field(
        default_factory=list,
        description="Task IDs in test split"
    )
    
    domain_distribution: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Domain counts per split"
    )
    
    failure_distribution: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Failure type counts per split"
    )
    
    @property
    def train_size(self) -> int:
        """Number of tasks in training set."""
        return len(self.train_ids)
    
    @property
    def val_size(self) -> int:
        """Number of tasks in validation set."""
        return len(self.val_ids)
    
    @property
    def test_size(self) -> int:
        """Number of tasks in test set."""
        return len(self.test_ids)
    
    @property
    def total_size(self) -> int:
        """Total number of tasks."""
        return self.train_size + self.val_size + self.test_size


class QualityMetrics(BaseModel):
    """Quality metrics for dataset."""
    
    completeness: float = Field(
        ge=0.0,
        le=1.0,
        description="Percentage of records with all required fields"
    )
    
    consistency: float = Field(
        ge=0.0,
        le=1.0,
        description="Percentage of trajectories with valid action sequences"
    )
    
    image_quality: float = Field(
        ge=0.0,
        le=1.0,
        description="Percentage of images with correct properties"
    )
    
    failure_coverage: int = Field(
        ge=0,
        description="Number of unique failure types"
    )
    
    domain_coverage: int = Field(
        ge=0,
        description="Number of unique domains"
    )
    
    recovery_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Percentage of failures with recovery attempts"
    )


class DatasetStatistics(BaseModel):
    """Complete dataset statistics."""
    
    total_tasks: int = Field(
        ge=0,
        description="Total number of tasks"
    )
    
    total_steps: int = Field(
        ge=0,
        description="Total number of steps"
    )
    
    total_failures: int = Field(
        ge=0,
        description="Total number of failures"
    )
    
    total_recoveries: int = Field(
        ge=0,
        description="Total number of recovery attempts"
    )
    
    successful_recoveries: int = Field(
        ge=0,
        description="Number of successful recoveries"
    )
    
    domains: List[str] = Field(
        default_factory=list,
        description="List of unique domains"
    )
    
    failure_types: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each failure type"
    )
    
    action_types: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each action type"
    )
    
    avg_trajectory_length: float = Field(
        ge=0.0,
        description="Average number of steps per trajectory"
    )
    
    quality_metrics: Optional[QualityMetrics] = Field(
        default=None,
        description="Quality metrics"
    )
    
    @property
    def failure_rate(self) -> float:
        """Overall failure rate."""
        if self.total_steps == 0:
            return 0.0
        return self.total_failures / self.total_steps
    
    @property
    def recovery_success_rate(self) -> float:
        """Recovery success rate."""
        if self.total_recoveries == 0:
            return 0.0
        return self.successful_recoveries / self.total_recoveries


# Default configurations
DEFAULT_VALIDATION_RULES = ValidationRule()
DEFAULT_SPLIT_CONFIG = SplitConfig()
