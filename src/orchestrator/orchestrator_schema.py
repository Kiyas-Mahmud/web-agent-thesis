"""
Orchestrator Schema

Data models for collection configuration, results, and statistics.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""
    
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class CollectionConfig(BaseModel):
    """Configuration for data collection orchestration."""
    
    # Dataset configuration
    dataset_name: str = Field(
        default="wave-ui",
        description="Dataset to collect from (wave-ui, mind2web, visualwebarena)"
    )
    
    num_tasks: int = Field(
        default=10,
        ge=1,
        description="Number of tasks to collect"
    )
    
    # Output configuration
    output_dir: Path = Field(
        default=Path("dataset"),
        description="Root directory for dataset output"
    )
    
    save_trajectories: bool = Field(
        default=True,
        description="Save trajectory JSONL files"
    )
    
    save_screenshots: bool = Field(
        default=True,
        description="Save screenshot images"
    )
    
    # Execution configuration
    max_workers: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of parallel workers"
    )
    
    timeout_per_task: int = Field(
        default=300,
        ge=30,
        description="Maximum seconds per task"
    )
    
    retry_on_failure: bool = Field(
        default=True,
        description="Retry failed tasks"
    )
    
    max_retries: int = Field(
        default=2,
        ge=0,
        description="Maximum retry attempts per task"
    )
    
    # Component configuration
    enable_metrics: bool = Field(
        default=True,
        description="Enable metric computation"
    )
    
    enable_failure_detection: bool = Field(
        default=True,
        description="Enable failure labeling"
    )
    
    enable_recovery: bool = Field(
        default=True,
        description="Enable recovery generation"
    )
    
    enable_reflection: bool = Field(
        default=True,
        description="Enable reflection annotation"
    )
    
    # Browser configuration
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    
    viewport_width: int = Field(
        default=1280,
        ge=800,
        description="Browser viewport width"
    )
    
    viewport_height: int = Field(
        default=720,
        ge=600,
        description="Browser viewport height"
    )


class TaskResult(BaseModel):
    """Result of processing a single task."""
    
    task_id: str = Field(
        description="Task identifier"
    )
    
    status: TaskStatus = Field(
        description="Execution status"
    )
    
    num_steps: int = Field(
        default=0,
        ge=0,
        description="Number of steps executed"
    )
    
    num_failures: int = Field(
        default=0,
        ge=0,
        description="Number of detected failures"
    )
    
    num_recoveries: int = Field(
        default=0,
        ge=0,
        description="Number of recovery attempts"
    )
    
    execution_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution time in seconds"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    output_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated output files (trajectory, images)"
    )


class PipelineStatistics(BaseModel):
    """Statistics for the entire collection pipeline."""
    
    total_tasks: int = Field(
        ge=0,
        description="Total tasks attempted"
    )
    
    successful_tasks: int = Field(
        ge=0,
        description="Successfully completed tasks"
    )
    
    failed_tasks: int = Field(
        ge=0,
        description="Failed tasks"
    )
    
    total_steps: int = Field(
        ge=0,
        description="Total steps executed across all tasks"
    )
    
    total_failures: int = Field(
        ge=0,
        description="Total failures detected"
    )
    
    total_recoveries: int = Field(
        ge=0,
        description="Total recovery attempts"
    )
    
    successful_recoveries: int = Field(
        ge=0,
        description="Successful recovery attempts"
    )
    
    total_execution_time: float = Field(
        ge=0.0,
        description="Total execution time in seconds"
    )
    
    @property
    def success_rate(self) -> float:
        """Task success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def failure_rate(self) -> float:
        """Step failure rate."""
        if self.total_steps == 0:
            return 0.0
        return self.total_failures / self.total_steps
    
    @property
    def recovery_success_rate(self) -> float:
        """Recovery success rate."""
        if self.total_recoveries == 0:
            return 0.0
        return self.successful_recoveries / self.total_recoveries
    
    @property
    def avg_steps_per_task(self) -> float:
        """Average steps per task."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_steps / self.total_tasks


class OrchestrationResult(BaseModel):
    """Complete result of orchestration run."""
    
    run_id: str = Field(
        description="Unique run identifier"
    )
    
    start_time: datetime = Field(
        description="Run start time"
    )
    
    end_time: datetime = Field(
        description="Run end time"
    )
    
    config: CollectionConfig = Field(
        description="Configuration used for run"
    )
    
    task_results: List[TaskResult] = Field(
        default_factory=list,
        description="Results for each task"
    )
    
    statistics: PipelineStatistics = Field(
        description="Aggregated statistics"
    )
    
    output_directory: Path = Field(
        description="Output directory path"
    )
    
    @property
    def duration_seconds(self) -> float:
        """Total run duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()


# Default configuration
DEFAULT_COLLECTION_CONFIG = CollectionConfig()
