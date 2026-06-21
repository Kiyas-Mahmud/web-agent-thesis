"""
Failure Labeler - Main Orchestration

Main class for processing trajectories and labeling failures. Integrates
detection, classification, and diagnosis to produce labeled trajectories.

Process Flow:
1. Load trajectory from JSONL file
2. For each step:
   - Load metrics (visual, state, performance)
   - Detect failure signals
   - Classify into failure type
   - Generate complete diagnosis
3. Aggregate trajectory-level statistics
4. Save labeled trajectory

Integration:
- Uses MetricComputer for step metrics
- Uses FailureDetector for signal detection
- Uses FailureClassifier for categorization
- Uses DiagnosticsEngine for complete diagnosis
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from ..metric_computation.metric_computer import MetricComputer
    from ..metric_computation.metric_schema import StepMetrics
except ImportError:
    from metric_computation.metric_computer import MetricComputer
    from metric_computation.metric_schema import StepMetrics

try:
    from .failure_schema import (
        FailureType,
        ExecutionOutcome,
        FailureLabel,
        LabeledStep,
        LabeledTrajectory,
        DiagnosticConfig,
        DEFAULT_DIAGNOSTIC_CONFIG,
    )
    from .failure_detector import FailureDetector
    from .failure_classifier import FailureClassifier
    from .diagnostics_engine import DiagnosticsEngine
except ImportError:
    from failure_labeling.failure_schema import (
        FailureType,
        ExecutionOutcome,
        FailureLabel,
        LabeledStep,
        LabeledTrajectory,
        DiagnosticConfig,
        DEFAULT_DIAGNOSTIC_CONFIG,
    )
    from failure_labeling.failure_detector import FailureDetector
    from failure_labeling.failure_classifier import FailureClassifier
    from failure_labeling.diagnostics_engine import DiagnosticsEngine


class FailureLabeler:
    """Main class for trajectory failure labeling.
    
    Processes recorded trajectories, computes metrics, detects failures,
    and generates labeled datasets with complete failure diagnoses.
    
    Usage:
        labeler = FailureLabeler(config)
        labeled_trajectory = labeler.process_trajectory_file("trajectory.jsonl")
        labeler.save_labeled_trajectory(labeled_trajectory, "labeled_trajectory.json")
    """
    
    def __init__(
        self,
        config: Optional[DiagnosticConfig] = None,
        metric_computer: Optional[MetricComputer] = None,
    ):
        """Initialize failure labeler.
        
        Args:
            config: Diagnostic configuration (uses default if not provided)
            metric_computer: Optional MetricComputer instance to reuse
        """
        self.config = config or DEFAULT_DIAGNOSTIC_CONFIG
        
        # Initialize components
        self.metric_computer = metric_computer or MetricComputer()
        self.detector = FailureDetector(self.config)
        self.classifier = FailureClassifier()
        self.diagnostics = DiagnosticsEngine(self.config)
    
    def label_step(
        self,
        step_data: Dict[str, Any],
        step_number: int,
        metrics: Optional[StepMetrics] = None,
        previous_url: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> LabeledStep:
        """Label a single step with failure diagnosis.
        
        Args:
            step_data: Step data from trajectory (action, args, status, etc.)
            step_number: Index of this step
            metrics: Optional pre-computed metrics
            previous_url: URL before action
            current_url: URL after action
            
        Returns:
            LabeledStep with failure diagnosis
        """
        # Extract action information
        action_type = step_data.get("action", {}).get("type", "unknown")
        action_args = step_data.get("action", {}).get("args", {})
        
        # Get action log for exception detection
        action_log = {
            "status": step_data.get("status", "success"),
            "error": step_data.get("error"),
            "completed": step_data.get("completed", True),
        }
        
        # Detect failure signals
        signals = self.detector.detect_all_signals(
            metrics,
            action_log,
            previous_url,
            current_url,
        )
        
        # Diagnose failure
        label = self.diagnostics.diagnose_from_signals(signals)
        
        # Create labeled step
        return LabeledStep(
            step_number=step_number,
            action_type=action_type,
            action_args=action_args,
            failure_label=label,
            timestamp=step_data.get("timestamp"),
            execution_time_ms=metrics.performance.execution_time_ms if metrics and metrics.performance else None,
        )
    
    def process_trajectory_file(
        self,
        trajectory_file: Path | str,
        compute_metrics: bool = True,
    ) -> LabeledTrajectory:
        """Process a trajectory file and label all failures.
        
        Args:
            trajectory_file: Path to trajectory JSONL file
            compute_metrics: Whether to compute metrics (requires screenshots)
            
        Returns:
            LabeledTrajectory with all steps labeled
        """
        trajectory_file = Path(trajectory_file)
        
        # Load trajectory
        steps_data = []
        with open(trajectory_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    steps_data.append(json.loads(line))
        
        # Extract trajectory metadata
        trajectory_id = trajectory_file.stem
        task_id = steps_data[0].get("task_id") if steps_data else None
        
        # Compute metrics if requested
        metrics_by_step = {}
        if compute_metrics:
            try:
                # Process trajectory through metric computer
                trajectory_metrics = self.metric_computer.process_trajectory_file(trajectory_file)
                
                # Map metrics to steps
                for step_metric in trajectory_metrics.get("step_metrics", []):
                    step_num = step_metric["step_number"]
                    metrics_by_step[step_num] = StepMetrics(**step_metric)
            except Exception as e:
                print(f"Warning: Could not compute metrics for {trajectory_file}: {e}")
                # Continue without metrics
        
        # Label each step
        labeled_steps = []
        for i, step_data in enumerate(steps_data):
            # Get URLs for UI variation detection
            previous_url = steps_data[i-1].get("url") if i > 0 else None
            current_url = step_data.get("url")
            
            # Get metrics for this step
            metrics = metrics_by_step.get(i)
            
            # Label the step
            labeled_step = self.label_step(
                step_data,
                step_number=i,
                metrics=metrics,
                previous_url=previous_url,
                current_url=current_url,
            )
            
            labeled_steps.append(labeled_step)
        
        # Compute trajectory-level statistics
        trajectory = self._create_labeled_trajectory(
            trajectory_id,
            task_id,
            labeled_steps,
        )
        
        return trajectory
    
    def _create_labeled_trajectory(
        self,
        trajectory_id: str,
        task_id: Optional[str],
        steps: List[LabeledStep],
    ) -> LabeledTrajectory:
        """Create LabeledTrajectory with aggregate statistics.
        
        Args:
            trajectory_id: Trajectory identifier
            task_id: Task identifier
            steps: List of labeled steps
            
        Returns:
            Complete LabeledTrajectory with statistics
        """
        # Count failures by type
        failure_summary = {}
        for step in steps:
            failure_type = step.failure_label.failure_type.value
            failure_summary[failure_type] = failure_summary.get(failure_type, 0) + 1
        
        # Count failed steps
        failed_steps = sum(
            1 for step in steps
            if step.failure_label.outcome == ExecutionOutcome.FAILURE
        )
        
        # Find first failure
        first_failure_step = None
        for step in steps:
            if step.failure_label.outcome == ExecutionOutcome.FAILURE:
                first_failure_step = step.step_number
                break
        
        # Determine overall outcome
        if failed_steps == 0:
            overall_outcome = ExecutionOutcome.SUCCESS
        elif failed_steps < len(steps) * 0.5:
            overall_outcome = ExecutionOutcome.PARTIAL_SUCCESS
        else:
            overall_outcome = ExecutionOutcome.FAILURE
        
        # Compute success rate
        success_rate = (len(steps) - failed_steps) / len(steps) if steps else 1.0
        
        return LabeledTrajectory(
            trajectory_id=trajectory_id,
            task_id=task_id,
            steps=steps,
            overall_outcome=overall_outcome,
            failure_summary=failure_summary,
            total_steps=len(steps),
            failed_steps=failed_steps,
            success_rate=success_rate,
            first_failure_step=first_failure_step,
        )
    
    def batch_process_trajectories(
        self,
        trajectory_dir: Path | str,
        output_dir: Path | str,
        pattern: str = "*.jsonl",
        compute_metrics: bool = True,
    ) -> Dict[str, Any]:
        """Process multiple trajectory files in batch.
        
        Args:
            trajectory_dir: Directory containing trajectory files
            output_dir: Directory to save labeled trajectories
            pattern: Glob pattern for trajectory files
            compute_metrics: Whether to compute metrics
            
        Returns:
            Dictionary with processing statistics
        """
        trajectory_dir = Path(trajectory_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all trajectory files
        trajectory_files = list(trajectory_dir.glob(pattern))
        
        results = {
            "total_trajectories": len(trajectory_files),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }
        
        for trajectory_file in trajectory_files:
            try:
                # Process trajectory
                labeled_trajectory = self.process_trajectory_file(
                    trajectory_file,
                    compute_metrics=compute_metrics,
                )
                
                # Save labeled trajectory
                output_file = output_dir / f"{trajectory_file.stem}_labeled.json"
                self.save_labeled_trajectory(labeled_trajectory, output_file)
                
                results["successful"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "file": str(trajectory_file),
                    "error": str(e),
                })
                print(f"Error processing {trajectory_file}: {e}")
        
        # Save batch summary
        summary_file = output_dir / "batch_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def save_labeled_trajectory(
        self,
        trajectory: LabeledTrajectory,
        output_file: Path | str,
    ) -> None:
        """Save labeled trajectory to JSON file.
        
        Args:
            trajectory: Labeled trajectory to save
            output_file: Output file path
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        trajectory_dict = trajectory.model_dump(mode='python')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trajectory_dict, f, indent=2)
    
    def generate_summary_report(
        self,
        trajectories: List[LabeledTrajectory],
    ) -> str:
        """Generate summary report for multiple trajectories.
        
        Args:
            trajectories: List of labeled trajectories
            
        Returns:
            Summary report string
        """
        if not trajectories:
            return "No trajectories to summarize."
        
        # Aggregate statistics
        total_steps = sum(t.total_steps for t in trajectories)
        total_failed_steps = sum(t.failed_steps for t in trajectories)
        
        # Count outcomes
        outcome_counts = {
            ExecutionOutcome.SUCCESS: 0,
            ExecutionOutcome.PARTIAL_SUCCESS: 0,
            ExecutionOutcome.FAILURE: 0,
        }
        for t in trajectories:
            outcome_counts[t.overall_outcome] += 1
        
        # Aggregate failure types
        failure_type_counts = {}
        for t in trajectories:
            for failure_type, count in t.failure_summary.items():
                failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + count
        
        # Build report
        lines = []
        lines.append(f"=== Failure Labeling Summary ===")
        lines.append(f"Total Trajectories: {len(trajectories)}")
        lines.append(f"Total Steps: {total_steps}")
        lines.append(f"Failed Steps: {total_failed_steps} ({total_failed_steps/total_steps*100:.1f}%)")
        lines.append(f"\nTrajectory Outcomes:")
        lines.append(f"  Success: {outcome_counts[ExecutionOutcome.SUCCESS]}")
        lines.append(f"  Partial Success: {outcome_counts[ExecutionOutcome.PARTIAL_SUCCESS]}")
        lines.append(f"  Failure: {outcome_counts[ExecutionOutcome.FAILURE]}")
        lines.append(f"\nFailure Type Distribution:")
        for failure_type, count in sorted(failure_type_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_steps * 100
            lines.append(f"  {failure_type}: {count} ({percentage:.1f}%)")
        
        return "\n".join(lines)
    
    def analyze_trajectory(self, trajectory: LabeledTrajectory) -> str:
        """Generate detailed analysis of a single trajectory.
        
        Args:
            trajectory: Labeled trajectory to analyze
            
        Returns:
            Detailed analysis report
        """
        lines = []
        lines.append(f"=== Trajectory Analysis: {trajectory.trajectory_id} ===")
        lines.append(f"Task ID: {trajectory.task_id or 'N/A'}")
        lines.append(f"Overall Outcome: {trajectory.overall_outcome.value}")
        lines.append(f"Success Rate: {trajectory.success_rate:.1%}")
        lines.append(f"Steps: {trajectory.total_steps} (Failed: {trajectory.failed_steps})")
        
        if trajectory.first_failure_step is not None:
            lines.append(f"First Failure: Step {trajectory.first_failure_step}")
        
        lines.append(f"\nFailure Summary:")
        for failure_type, count in trajectory.failure_summary.items():
            lines.append(f"  {failure_type}: {count}")
        
        lines.append(f"\nStep-by-Step Analysis:")
        for step in trajectory.steps:
            label = step.failure_label
            summary = self.diagnostics.summarize_diagnosis(label)
            lines.append(f"\nStep {step.step_number}: {step.action_type}")
            lines.append(f"  {summary}")
        
        return "\n".join(lines)
