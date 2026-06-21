"""
Metric Computer

Main class for computing metrics on browser interaction trajectories.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
import time
import json

from .metric_schema import (
    StepMetrics,
    TrajectoryMetrics,
    VisualMetrics,
    StateHashMetrics,
    PerformanceMetrics,
    MetricThresholds,
    ChangeLevel
)
from .visual_metrics import VisualMetricsComputer
from .state_hash import StateHashComputer

logger = logging.getLogger(__name__)


class MetricComputer:
    """
    Main class for computing metrics on browser interaction trajectories.
    
    Integrates:
    - Visual difference computation
    - State hashing and loop detection
    - Performance metrics aggregation
    """
    
    def __init__(
        self,
        thresholds: Optional[MetricThresholds] = None,
        output_dir: str = "dataset"
    ):
        """
        Initialize metric computer.
        
        Args:
            thresholds: Metric thresholds for classification
            output_dir: Base directory for dataset
        """
        self.thresholds = thresholds or MetricThresholds()
        self.output_dir = Path(output_dir)
        
        # Initialize sub-computers
        self.visual_computer = VisualMetricsComputer(self.thresholds)
        self.state_computer = StateHashComputer(self.thresholds)
        
        # Metrics storage
        self.metrics_dir = self.output_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("MetricComputer initialized")
    
    def compute_step_metrics(
        self,
        step_id: int,
        before_screenshot: Union[str, Path],
        after_screenshot: Union[str, Path],
        execution_time_ms: float = 0.0,
        stability_wait_ms: float = 0.0
    ) -> StepMetrics:
        """
        Compute all metrics for a single step.
        
        Args:
            step_id: Step identifier
            before_screenshot: Path to before screenshot
            after_screenshot: Path to after screenshot
            execution_time_ms: Action execution time
            stability_wait_ms: Time waited for stability
        
        Returns:
            StepMetrics object with all computed metrics
        """
        logger.debug(f"Computing metrics for step {step_id}")
        
        start_time = time.time()
        
        # Compute visual metrics
        visual_metrics = self.visual_computer.compute_metrics(
            before_screenshot,
            after_screenshot
        )
        
        # Compute state hash for after screenshot
        state_hash_metrics = self.state_computer.compute_hashes(after_screenshot)
        
        # Create performance metrics
        screenshot_time = (time.time() - start_time) * 1000  # Mock times for now
        performance_metrics = PerformanceMetrics(
            execution_time_ms=execution_time_ms,
            stability_wait_ms=stability_wait_ms,
            screenshot_before_time_ms=screenshot_time / 2,
            screenshot_after_time_ms=screenshot_time / 2,
            total_step_time_ms=execution_time_ms + stability_wait_ms + screenshot_time
        )
        
        # Create step metrics
        step_metrics = StepMetrics(
            step_id=step_id,
            visual=visual_metrics,
            state_hash=state_hash_metrics,
            performance=performance_metrics
        )
        
        logger.debug(f"Step {step_id} metrics: diff={visual_metrics.pixel_diff_score:.3f}, "
                    f"ssim={visual_metrics.ssim_score:.3f}, "
                    f"change={visual_metrics.change_level.value}")
        
        return step_metrics
    
    def compute_trajectory_metrics(
        self,
        trajectory_data: Dict[str, Any],
        image_dir: Optional[Path] = None
    ) -> TrajectoryMetrics:
        """
        Compute aggregate metrics for entire trajectory.
        
        Args:
            trajectory_data: Trajectory dictionary with steps
            image_dir: Directory containing screenshots (optional)
        
        Returns:
            TrajectoryMetrics with aggregate statistics
        """
        task_id = trajectory_data.get('task_id', 'unknown')
        steps = trajectory_data.get('steps', [])
        
        logger.info(f"Computing trajectory metrics for {task_id} ({len(steps)} steps)")
        
        # Reset state computer for new trajectory
        self.state_computer.reset()
        
        # Initialize counters
        total_steps = len(steps)
        successful_steps = 0
        failed_steps = 0
        visual_diffs = []
        ssim_scores = []
        major_changes = 0
        minor_changes = 0
        no_changes = 0
        
        # Process each step
        for i, step in enumerate(steps):
            step_id = step.get('step_id', i + 1)
            result = step.get('result', {})
            
            # Count success/failure
            if result.get('success', False):
                successful_steps += 1
            else:
                failed_steps += 1
            
            # Compute visual metrics if screenshots available
            screenshot_before = step.get('screenshot_before')
            screenshot_after = step.get('screenshot_after')
            
            if screenshot_before and screenshot_after and image_dir:
                try:
                    before_path = image_dir / screenshot_before
                    after_path = image_dir / screenshot_after
                    
                    if before_path.exists() and after_path.exists():
                        # Compute visual metrics
                        visual_metrics = self.visual_computer.compute_metrics(
                            before_path,
                            after_path
                        )
                        
                        visual_diffs.append(visual_metrics.pixel_diff_score)
                        ssim_scores.append(visual_metrics.ssim_score)
                        
                        # Count change types
                        if visual_metrics.change_level == ChangeLevel.MAJOR_CHANGE:
                            major_changes += 1
                        elif visual_metrics.change_level == ChangeLevel.MINOR_CHANGE:
                            minor_changes += 1
                        else:
                            no_changes += 1
                        
                        # Compute state hash
                        self.state_computer.compute_hashes(after_path)
                    
                except Exception as e:
                    logger.warning(f"Failed to compute metrics for step {step_id}: {e}")
        
        # Get duration
        start_time = trajectory_data.get('start_time', 0)
        end_time = trajectory_data.get('end_time', start_time)
        total_duration = end_time - start_time
        
        # Get state statistics
        state_summary = self.state_computer.get_state_summary()
        
        # Create trajectory metrics
        trajectory_metrics = TrajectoryMetrics(
            task_id=task_id,
            total_steps=total_steps,
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            total_duration_seconds=total_duration,
            avg_visual_diff=sum(visual_diffs) / len(visual_diffs) if visual_diffs else 0.0,
            avg_ssim=sum(ssim_scores) / len(ssim_scores) if ssim_scores else 0.0,
            loops_detected=state_summary.get('loop_states', 0),
            duplicate_states=state_summary.get('duplicate_states', 0),
            unique_states=state_summary.get('unique_states', 0),
            major_changes=major_changes,
            minor_changes=minor_changes,
            no_changes=no_changes
        )
        
        logger.info(f"Trajectory {task_id}: {successful_steps}/{total_steps} successful, "
                   f"{trajectory_metrics.unique_states} unique states, "
                   f"{trajectory_metrics.loops_detected} loops")
        
        return trajectory_metrics
    
    def process_trajectory_file(
        self,
        trajectory_file: Union[str, Path],
        image_dir: Optional[Union[str, Path]] = None
    ) -> TrajectoryMetrics:
        """
        Load and process a trajectory JSONL file.
        
        Args:
            trajectory_file: Path to trajectory JSONL file
            image_dir: Directory containing screenshots
        
        Returns:
            TrajectoryMetrics object
        """
        trajectory_file = Path(trajectory_file)
        
        if not trajectory_file.exists():
            raise FileNotFoundError(f"Trajectory file not found: {trajectory_file}")
        
        # Load trajectory data (last line of JSONL)
        with open(trajectory_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                raise ValueError(f"Empty trajectory file: {trajectory_file}")
            
            # Get last trajectory
            trajectory_data = json.loads(lines[-1])
        
        # Set image directory
        if image_dir is None:
            image_dir = self.output_dir / "images"
        else:
            image_dir = Path(image_dir)
        
        # Compute metrics
        metrics = self.compute_trajectory_metrics(trajectory_data, image_dir)
        
        # Save metrics
        self.save_trajectory_metrics(metrics)
        
        return metrics
    
    def save_trajectory_metrics(self, metrics: TrajectoryMetrics):
        """
        Save trajectory metrics to file.
        
        Args:
            metrics: TrajectoryMetrics to save
        """
        output_file = self.metrics_dir / f"{metrics.task_id}_metrics.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metrics saved: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def batch_process_trajectories(
        self,
        trajectory_dir: Union[str, Path],
        image_dir: Optional[Union[str, Path]] = None
    ) -> List[TrajectoryMetrics]:
        """
        Process all trajectory files in a directory.
        
        Args:
            trajectory_dir: Directory containing trajectory JSONL files
            image_dir: Directory containing screenshots
        
        Returns:
            List of TrajectoryMetrics objects
        """
        trajectory_dir = Path(trajectory_dir)
        
        if not trajectory_dir.exists():
            raise FileNotFoundError(f"Trajectory directory not found: {trajectory_dir}")
        
        # Find all JSONL files
        trajectory_files = list(trajectory_dir.glob("*.jsonl"))
        
        logger.info(f"Processing {len(trajectory_files)} trajectory files")
        
        all_metrics = []
        
        for trajectory_file in trajectory_files:
            try:
                metrics = self.process_trajectory_file(trajectory_file, image_dir)
                all_metrics.append(metrics)
            except Exception as e:
                logger.error(f"Failed to process {trajectory_file}: {e}")
        
        logger.info(f"Processed {len(all_metrics)}/{len(trajectory_files)} trajectories")
        
        # Save aggregate summary
        self.save_aggregate_summary(all_metrics)
        
        return all_metrics
    
    def save_aggregate_summary(self, all_metrics: List[TrajectoryMetrics]):
        """
        Save aggregate summary of all metrics.
        
        Args:
            all_metrics: List of TrajectoryMetrics
        """
        if not all_metrics:
            return
        
        summary = {
            'total_trajectories': len(all_metrics),
            'total_steps': sum(m.total_steps for m in all_metrics),
            'total_successful_steps': sum(m.successful_steps for m in all_metrics),
            'total_failed_steps': sum(m.failed_steps for m in all_metrics),
            'avg_steps_per_trajectory': sum(m.total_steps for m in all_metrics) / len(all_metrics),
            'avg_visual_diff': sum(m.avg_visual_diff for m in all_metrics) / len(all_metrics),
            'avg_ssim': sum(m.avg_ssim for m in all_metrics) / len(all_metrics),
            'total_loops': sum(m.loops_detected for m in all_metrics),
            'total_unique_states': sum(m.unique_states for m in all_metrics),
            'trajectories_with_loops': sum(1 for m in all_metrics if m.loops_detected > 0)
        }
        
        output_file = self.metrics_dir / "aggregate_summary.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Aggregate summary saved: {output_file}")
    
    def get_thresholds(self) -> MetricThresholds:
        """Get current metric thresholds"""
        return self.thresholds
    
    def update_thresholds(self, thresholds: MetricThresholds):
        """Update metric thresholds"""
        self.thresholds = thresholds
        self.visual_computer.thresholds = thresholds
        self.state_computer.thresholds = thresholds
        logger.info("Metric thresholds updated")
