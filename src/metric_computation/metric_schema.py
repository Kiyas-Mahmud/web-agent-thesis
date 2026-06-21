"""
Metric Schema

Pydantic models for metric computation results.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import time


class ChangeLevel(str, Enum):
    """Visual change classification"""
    NO_CHANGE = "no_change"         # < 5% difference
    MINOR_CHANGE = "minor_change"   # 5-30% difference
    MAJOR_CHANGE = "major_change"   # > 30% difference


class VisualMetrics(BaseModel):
    """Visual difference metrics between two images"""
    
    pixel_diff_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Normalized pixel-level difference (0=identical, 1=completely different)"
    )
    
    ssim_score: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Structural Similarity Index (1=identical, -1=opposite)"
    )
    
    mse: float = Field(
        ..., 
        ge=0.0,
        description="Mean Squared Error between images"
    )
    
    change_level: ChangeLevel = Field(
        ...,
        description="Classification of visual change magnitude"
    )
    
    computation_time_ms: float = Field(
        default=0.0,
        description="Time taken to compute visual metrics"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = self.model_dump()
        data['change_level'] = self.change_level.value
        return data


class StateHashMetrics(BaseModel):
    """State hashing and loop detection metrics"""
    
    state_hash: str = Field(
        ...,
        description="SHA-256 hash of image state"
    )
    
    perceptual_hash: str = Field(
        ...,
        description="Perceptual hash for similarity detection"
    )
    
    perceptual_hash_diff: Optional[int] = Field(
        default=None,
        description="Hamming distance from previous state (None if first state)"
    )
    
    is_duplicate: bool = Field(
        default=False,
        description="True if state is identical to previous state"
    )
    
    loop_detected: bool = Field(
        default=False,
        description="True if state appears to be in a loop"
    )
    
    state_occurrences: int = Field(
        default=1,
        description="Number of times this state has been seen"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()


class PerformanceMetrics(BaseModel):
    """Performance and timing metrics"""
    
    execution_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Action execution time in milliseconds"
    )
    
    stability_wait_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time waited for page to stabilize"
    )
    
    screenshot_before_time_ms: float = Field(
        default=0.0,
        description="Time to capture before screenshot"
    )
    
    screenshot_after_time_ms: float = Field(
        default=0.0,
        description="Time to capture after screenshot"
    )
    
    total_step_time_ms: float = Field(
        default=0.0,
        description="Total time for complete step"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()


class StepMetrics(BaseModel):
    """Complete metrics for a single step"""
    
    step_id: int = Field(..., description="Step identifier")
    
    visual: Optional[VisualMetrics] = Field(
        default=None,
        description="Visual difference metrics"
    )
    
    state_hash: StateHashMetrics = Field(
        ...,
        description="State hashing metrics"
    )
    
    performance: PerformanceMetrics = Field(
        ...,
        description="Performance metrics"
    )
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Timestamp when metrics were computed"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'step_id': self.step_id,
            'timestamp': self.timestamp
        }
        
        if self.visual:
            data['visual'] = self.visual.to_dict()
        
        data['state_hash'] = self.state_hash.to_dict()
        data['performance'] = self.performance.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepMetrics':
        """Create from dictionary"""
        if 'visual' in data and data['visual']:
            data['visual'] = VisualMetrics(**data['visual'])
        
        if 'state_hash' in data:
            data['state_hash'] = StateHashMetrics(**data['state_hash'])
        
        if 'performance' in data:
            data['performance'] = PerformanceMetrics(**data['performance'])
        
        return cls(**data)


class TrajectoryMetrics(BaseModel):
    """Aggregate metrics for entire trajectory"""
    
    task_id: str = Field(..., description="Task identifier")
    
    total_steps: int = Field(default=0, description="Total number of steps")
    
    successful_steps: int = Field(default=0, description="Steps with success=True")
    
    failed_steps: int = Field(default=0, description="Steps with success=False")
    
    total_duration_seconds: float = Field(
        default=0.0,
        description="Total trajectory duration"
    )
    
    avg_visual_diff: float = Field(
        default=0.0,
        description="Average visual difference across steps"
    )
    
    avg_ssim: float = Field(
        default=0.0,
        description="Average SSIM score across steps"
    )
    
    loops_detected: int = Field(
        default=0,
        description="Number of loops detected"
    )
    
    duplicate_states: int = Field(
        default=0,
        description="Number of duplicate states"
    )
    
    unique_states: int = Field(
        default=0,
        description="Number of unique states visited"
    )
    
    major_changes: int = Field(
        default=0,
        description="Number of steps with major visual changes"
    )
    
    minor_changes: int = Field(
        default=0,
        description="Number of steps with minor visual changes"
    )
    
    no_changes: int = Field(
        default=0,
        description="Number of steps with no visual changes"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrajectoryMetrics':
        """Create from dictionary"""
        return cls(**data)


class MetricThresholds(BaseModel):
    """Configurable thresholds for metric interpretation"""
    
    # Visual difference thresholds
    visual_diff_no_change: float = Field(default=0.05, description="Below this = no change")
    visual_diff_major_change: float = Field(default=0.30, description="Above this = major change")
    
    # SSIM thresholds
    ssim_no_change: float = Field(default=0.95, description="Above this = no change")
    ssim_major_change: float = Field(default=0.70, description="Below this = major change")
    
    # Perceptual hash thresholds
    phash_no_change: int = Field(default=5, description="Below this = no change")
    phash_major_change: int = Field(default=15, description="Above this = major change")
    
    # Loop detection
    loop_history_size: int = Field(default=20, description="Number of recent states to check")
    loop_occurrence_threshold: int = Field(default=3, description="Occurrences before declaring loop")
    
    # Performance thresholds (warning levels)
    slow_action_ms: float = Field(default=5000.0, description="Action slower than this is flagged")
    slow_step_ms: float = Field(default=10000.0, description="Step slower than this is flagged")
    
    def classify_visual_change(self, pixel_diff: float, ssim: float) -> ChangeLevel:
        """
        Classify visual change based on thresholds.
        
        Args:
            pixel_diff: Pixel difference score (0-1)
            ssim: SSIM score (-1 to 1)
        
        Returns:
            ChangeLevel classification
        """
        # Use both metrics - if either indicates major change, classify as major
        if pixel_diff > self.visual_diff_major_change or ssim < self.ssim_major_change:
            return ChangeLevel.MAJOR_CHANGE
        elif pixel_diff < self.visual_diff_no_change and ssim > self.ssim_no_change:
            return ChangeLevel.NO_CHANGE
        else:
            return ChangeLevel.MINOR_CHANGE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
