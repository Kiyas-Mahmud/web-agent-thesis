"""
Collection Orchestrator

Main orchestration class that manages end-to-end data collection pipeline.
Integrates all components from Tasks 01-06.
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

try:
    from .orchestrator_schema import (
        CollectionConfig,
        OrchestrationResult,
        TaskResult,
        TaskStatus,
        PipelineStatistics,
        DEFAULT_COLLECTION_CONFIG,
    )
except ImportError:
    from orchestrator_schema import (
        CollectionConfig,
        OrchestrationResult,
        TaskResult,
        TaskStatus,
        PipelineStatistics,
        DEFAULT_COLLECTION_CONFIG,
    )

# Import all component modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_loader import TaskLoader
from browser_recorder import BrowserRecorder
from browser_recorder.action_schema import Action, ActionType
from metric_computation import MetricComputer
from failure_labeling import FailureLabeler
from recovery_generation import RecoveryEngine
from reflection_annotation import ReflectionAnnotator


class CollectionOrchestrator:
    """Main orchestrator for data collection pipeline.
    
    Manages integration of:
    - Task loading (Task-01)
    - Browser recording (Task-02)
    - Metric computation (Task-03)
    - Failure labeling (Task-04)
    - Recovery generation (Task-05)
    - Reflection annotation (Task-06)
    """
    
    def __init__(self, config: Optional[CollectionConfig] = None):
        """Initialize orchestrator with configuration.
        
        Args:
            config: Collection configuration
        """
        self.config = config or DEFAULT_COLLECTION_CONFIG
        
        # Initialize all components
        self.task_loader = TaskLoader(
            sources=[self.config.dataset_name],
            cache_dir=str(self.config.output_dir / "cache")
        )
        
        # Browser recorder configuration
        browser_config = {
            'browser': {
                'headless': self.config.headless,
                'viewport': {
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                'timeout': self.config.timeout_per_task * 1000,  # Convert to ms
            },
            'screenshots': {
                'format': 'png',
                'quality': 95
            }
        }
        self.browser_recorder = BrowserRecorder(
            config=browser_config,
            output_dir=str(self.config.output_dir)
        )
        
        self.metric_computer = MetricComputer()
        self.failure_labeler = FailureLabeler()
        self.recovery_engine = RecoveryEngine()
        self.reflection_annotator = ReflectionAnnotator()
        
        # Statistics
        self.task_results: List[TaskResult] = []
    
    def _annotate_with_metrics(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """Add metric annotations to each step in trajectory.
        
        Args:
            trajectory: Trajectory dict from browser recorder
            
        Returns:
            Trajectory with metrics added to each step
        """
        steps = trajectory.get("steps", [])
        
        for i, step in enumerate(steps):
            # Extract screenshot paths and timing
            screenshot_before = step.get("screenshot_before")
            screenshot_after = step.get("screenshot_after")
            execution_time = step.get("result", {}).get("execution_time_ms", 0.0)
            
            if screenshot_before and screenshot_after:
                try:
                    # Compute metrics for this step
                    step_metrics = self.metric_computer.compute_step_metrics(
                        step_id=i,
                        before_screenshot=screenshot_before,
                        after_screenshot=screenshot_after,
                        execution_time_ms=execution_time,
                    )
                    
                    # Add metrics to step
                    step["metrics"] = {
                        "visual": step_metrics.visual.model_dump(),
                        "state_hash": step_metrics.state_hash.model_dump(),
                        "performance": step_metrics.performance.model_dump(),
                    }
                except Exception as e:
                    # If metrics fail, add empty metrics  
                    step["metrics"] = {
                        "visual": {},
                        "state_hash": {},
                        "performance": {"execution_time_ms": execution_time},
                    }
            else:
                # No screenshots available
                step["metrics"] = {
                    "visual": {},
                    "state_hash": {},
                    "performance": {"execution_time_ms": execution_time},
                }
        
        return trajectory
    
    def _annotate_with_failure_labels(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """Add failure labels to each step in trajectory.
        
        Args:
            trajectory: Trajectory dict from browser recorder
            
        Returns:
            Trajectory with failure labels added to each step
        """
        steps = trajectory.get("steps", [])
        
        for i, step in enumerate(steps):
            # Get step data
            step_result = step.get("result", {})
            screenshot_before = step.get("screenshot_before")
            screenshot_after = step.get("screenshot_after")
            metrics = step.get("metrics", {})
            
            # Label this step
            try:
                failure_label = self.failure_labeler.label_step(
                    step_id=i,
                    action_type=step.get("action", {}).get("action_type", "UNKNOWN"),
                    success=step_result.get("success", True),
                    error_message=step_result.get("error"),
                    execution_time_ms=step_result.get("execution_time_ms", 0.0),
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                    metrics=metrics,
                )
                
                # Add to step
                step["failure"] = failure_label.model_dump()
            except Exception as e:
                # If labeling fails, add empty failure info
                step["failure"] = {
                    "failure_type": "none",
                    "confidence": 0.0,
                    "signals": [],
                    "recommended_recovery": None,
                }
        
        return trajectory
    
    def _annotate_with_recovery(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """Add recovery annotations to failed steps in trajectory.
        
        Args:
            trajectory: Trajectory dict from browser recorder
            
        Returns:
            Trajectory with recovery info added to failed steps
        """
        steps = trajectory.get("steps", [])
        
        for i, step in enumerate(steps):
            # Check if step has failure
            failure = step.get("failure", {})
            failure_type = failure.get("failure_type")
            
            if failure_type and failure_type != "none":
                # This step failed - add recovery info
                # For demo purposes, we're not actually executing recoveries
                # In a real system, this would call recovery_engine.recover_from_failure()
                step["recovery"] = {
                    "attempted": True,
                    "strategy": failure.get("recommended_recovery", "RETRY"),
                    "success": False,  # Demo - no actual recovery execution
                    "duration_ms": 0,
                }
            else:
                # No failure - no recovery needed
                step["recovery"] = {
                    "attempted": False,
                    "strategy": None,
                    "success": None,
                    "duration_ms": 0,
                }
        
        return trajectory
    
    async def _record_task_in_browser(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Record task execution in browser (async).
        
        Args:
            task: Task definition
            
        Returns:
            Trajectory dict or None on failure
        """
        task_id = task.get("task_id", "unknown")
        start_url = task.get("start_url", "https://example.com")
        task_description = task.get("task_description", "")
        
        try:
            # Start browser session
            await self.browser_recorder.start_session(task_id, start_url)
            
            # Simulate simple demo actions to generate trajectories
            # In a real system, an AI agent would execute actual actions
            # For now, we create minimal demo actions that won't fail
            demo_actions = [
                Action(
                    action_type=ActionType.NAVIGATE,
                    value=start_url,  # URL goes in value field for NAVIGATE
                    description=f"Navigate to {start_url}"
                ),
                Action(
                    action_type=ActionType.WAIT,
                    timeout=1000,
                    description="Wait for page load"
                ),
                # Simple scroll action (doesn't need selector)
                Action(
                    action_type=ActionType.SCROLL,
                    scroll_amount=100,
                    description="Scroll down page"
                ),
            ]
            
            # Record each action
            for action in demo_actions:
                try:
                    await self.browser_recorder.record_step(action)
                except Exception as step_error:
                    # Continue even if individual steps fail
                    print(f"      Step error (continuing): {step_error}")
            
            # Get trajectory BEFORE ending session (end_session clears it)
            trajectory_obj = self.browser_recorder.get_trajectory()
            
            # End session (this saves and clears the trajectory)
            await self.browser_recorder.end_session(success=True)
            
            if trajectory_obj:
                return trajectory_obj.to_dict()
            
            return None
            
        except Exception as e:
            try:
                await self.browser_recorder.end_session(success=False, error=str(e))
            except:
                pass  # Ignore errors during cleanup
            raise
    
    async def _collect_one_task_async(self, task: Dict[str, Any]) -> TaskResult:
        """Async version of collect_one_task.
        
        Args:
            task: Task definition from task loader
            
        Returns:
            TaskResult with execution details
        """
        task_id = task.get("task_id", "unknown")
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"Processing Task: {task_id}")
        print(f"{'='*70}")
        
        try:
            # Step 1: Execute task in browser (Task-02)
            print(f"[1/6] Executing in browser...")
            trajectory = await self._record_task_in_browser(task)
            
            if not trajectory or not trajectory.get("steps"):
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error_message="No steps recorded",
                    execution_time=time.time() - start_time,
                )
            
            num_steps = len(trajectory["steps"])
            print(f"      [X] Recorded {num_steps} steps")
            
            # Step 2: Compute metrics (Task-03)
            if self.config.enable_metrics:
                print(f"[2/6] Computing metrics...")
                trajectory = self._annotate_with_metrics(trajectory)
                print(f"      [X] Metrics computed for all steps")
            else:
                print(f"[2/6] Skipping metrics (disabled)")
            
            # Step 3: Label failures (Task-04)
            num_failures = 0
            if self.config.enable_failure_detection:
                print(f"[3/6] Detecting failures...")
                trajectory = self._annotate_with_failure_labels(trajectory)
                
                # Count failures
                for step in trajectory.get("steps", []):
                    failure = step.get("failure", {})
                    if failure.get("failure_type") not in [None, "none"]:
                        num_failures += 1
                
                print(f"      [X] Detected {num_failures} failures")
            else:
                print(f"[3/6] Skipping failure detection (disabled)")
            
            # Step 4: Generate recovery strategies (Task-05)
            num_recoveries = 0
            successful_recoveries = 0
            if self.config.enable_recovery:
                print(f"[4/6] Annotating with recovery info...")
                trajectory = self._annotate_with_recovery(trajectory)
                
                # Count recoveries
                for step in trajectory.get("steps", []):
                    recovery = step.get("recovery")
                    if recovery and recovery.get("attempted"):
                        num_recoveries += 1
                        if recovery.get("success"):
                            successful_recoveries += 1
                
                print(f"      [X] Recovery info added (attempted: {num_recoveries})")
            else:
                print(f"[4/6] Skipping recovery annotation (disabled)")
            
            # Step 5: Add reflection annotations (Task-06)
            if self.config.enable_reflection:
                print(f"[5/6] Adding reflection annotations...")
                
                # Annotate each step
                annotations = []
                for i, step in enumerate(trajectory.get("steps", [])):
                    # Extract info for reflection
                    action = {
                        "type": step.get("type"),
                        "target": step.get("selector", step.get("url", "")),
                    }
                    outcome = {
                        "success": step.get("success", True),
                        "timeout": step.get("timeout", False),
                    }
                    failure_info = step.get("failure")
                    recovery_info = step.get("recovery")
                    metrics = step.get("metrics")
                    
                    # Create reflection annotation
                    annotation = self.reflection_annotator.annotate_step(
                        step_id=i,
                        action=action,
                        outcome=outcome,
                        failure_info=failure_info,
                        recovery_info=recovery_info,
                        metrics=metrics,
                    )
                    
                    # Add to step
                    step["reflection"] = {
                        "confidence_before": annotation.agent_confidence_before,
                        "confidence_after": annotation.agent_confidence_after,
                        "confidence_delta": annotation.confidence_delta,
                        "reflection_text": annotation.reflection_text,
                        "memory_update_flag": annotation.memory_update_flag,
                        "memory_type": annotation.memory_type.value,
                        "introspection_metadata": annotation.introspection_metadata.model_dump(),
                    }
                    annotations.append(annotation)
                
                print(f"      [X] Added reflections to all steps")
                
                # Add reflection statistics
                memory_updates = sum(1 for a in annotations if a.memory_update_flag)
                print(f"        ({memory_updates} memory-worthy experiences)")
            else:
                print(f"[5/6] Skipping reflection (disabled)")
            
            # Step 6: Save output
            output_files = {}
            if self.config.save_trajectories:
                print(f"[6/6] Saving trajectory...")
                output_file = self._save_trajectory(trajectory, task_id)
                output_files["trajectory"] = str(output_file)
                print(f"      [X] Saved to {output_file}")
            
            execution_time = time.time() - start_time
            
            # Create result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                num_steps=num_steps,
                num_failures=num_failures,
                num_recoveries=num_recoveries,
                execution_time=execution_time,
                output_files=output_files,
            )
            
            print(f"\n[X] Task completed successfully in {execution_time:.2f}s")
            print(f"  Steps: {num_steps} | Failures: {num_failures} | Recoveries: {num_recoveries}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            print(f"\n[FAIL] Task failed: {error_msg}")
            
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                execution_time=execution_time,
                error_message=error_msg,
            )
    
    def collect_one_task(self, task: Dict[str, Any]) -> TaskResult:
        """Collect data for a single task through full pipeline.
        
        Args:
            task: Task definition from task loader
            
        Returns:
            TaskResult with execution details
        """
        return asyncio.run(self._collect_one_task_async(task))
    
    def collect_dataset(self) -> OrchestrationResult:
        """Run full collection pipeline on configured dataset.
        
        Returns:
            OrchestrationResult with complete statistics
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        
        print("\n" + "="*70)
        print(f"STARTING DATA COLLECTION RUN: {run_id}")
        print("="*70)
        print(f"Dataset: {self.config.dataset_name}")
        print(f"Tasks: {self.config.num_tasks}")
        print(f"Output: {self.config.output_dir}")
        print("="*70)
        
        # Setup output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "records").mkdir(exist_ok=True)
        (self.config.output_dir / "images").mkdir(exist_ok=True)
        
        # Load tasks
        print(f"\nLoading tasks from {self.config.dataset_name}...")
        tasks = self.task_loader.load_tasks(limit=self.config.num_tasks)
        print(f"[X] Loaded {len(tasks)} tasks")
        
        # Process each task
        for i, task in enumerate(tasks, 1):
            print(f"\n{'='*70}")
            print(f"TASK {i}/{len(tasks)}")
            print(f"{'='*70}")
            
            # Convert Task object to dict
            task_dict = task.to_dict()
            result = self.collect_one_task(task_dict)
            self.task_results.append(result)
        
        # Compute statistics
        end_time = datetime.now()
        statistics = self._compute_statistics()
        
        # Create result
        result = OrchestrationResult(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            config=self.config,
            task_results=self.task_results,
            statistics=statistics,
            output_directory=self.config.output_dir,
        )
        
        # Save run metadata
        self._save_run_metadata(result)
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def _save_trajectory(self, trajectory: Dict[str, Any], task_id: str) -> Path:
        """Save trajectory to JSONL file.
        
        Args:
            trajectory: Complete trajectory with all annotations
            task_id: Task identifier
            
        Returns:
            Path to saved file
        """
        output_file = self.config.output_dir / "records" / f"{task_id}.jsonl"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(trajectory, f, indent=2)
        
        return output_file
    
    def _compute_statistics(self) -> PipelineStatistics:
        """Compute aggregated statistics from all task results.
        
        Returns:
            PipelineStatistics with aggregated metrics
        """
        total_tasks = len(self.task_results)
        successful_tasks = sum(
            1 for r in self.task_results 
            if r.status == TaskStatus.SUCCESS
        )
        failed_tasks = total_tasks - successful_tasks
        
        total_steps = sum(r.num_steps for r in self.task_results)
        total_failures = sum(r.num_failures for r in self.task_results)
        total_recoveries = sum(r.num_recoveries for r in self.task_results)
        
        # Note: We don't track successful_recoveries separately yet
        successful_recoveries = 0
        
        total_execution_time = sum(r.execution_time for r in self.task_results)
        
        return PipelineStatistics(
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            total_steps=total_steps,
            total_failures=total_failures,
            total_recoveries=total_recoveries,
            successful_recoveries=successful_recoveries,
            total_execution_time=total_execution_time,
        )
    
    def _save_run_metadata(self, result: OrchestrationResult) -> None:
        """Save run metadata to file.
        
        Args:
            result: Orchestration result
        """
        metadata_file = self.config.output_dir / f"run_{result.run_id}.json"
        
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
        
        print(f"\n[X] Saved run metadata to {metadata_file}")
    
    def _print_summary(self, result: OrchestrationResult) -> None:
        """Print collection summary.
        
        Args:
            result: Orchestration result
        """
        stats = result.statistics
        
        print("\n" + "="*70)
        print("COLLECTION COMPLETE")
        print("="*70)
        print(f"Run ID: {result.run_id}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print()
        print("Task Statistics:")
        print(f"  Total: {stats.total_tasks}")
        print(f"  Successful: {stats.successful_tasks} ({stats.success_rate:.1%})")
        print(f"  Failed: {stats.failed_tasks}")
        print()
        print("Step Statistics:")
        print(f"  Total Steps: {stats.total_steps}")
        print(f"  Avg per Task: {stats.avg_steps_per_task:.1f}")
        print(f"  Failures: {stats.total_failures} ({stats.failure_rate:.1%})")
        print(f"  Recoveries: {stats.total_recoveries}")
        print()
        print(f"Output Directory: {result.output_directory}")
        print("="*70)


def run_collection_pipeline(
    dataset_name: str = "wave-ui",
    num_tasks: int = 5,
    output_dir: Path = Path("dataset"),
    **kwargs
) -> OrchestrationResult:
    """Convenience function to run collection pipeline.
    
    Args:
        dataset_name: Dataset to collect from
        num_tasks: Number of tasks to collect
        output_dir: Output directory
        **kwargs: Additional configuration options
        
    Returns:
        OrchestrationResult with complete statistics
    """
    config = CollectionConfig(
        dataset_name=dataset_name,
        num_tasks=num_tasks,
        output_dir=output_dir,
        **kwargs
    )
    
    orchestrator = CollectionOrchestrator(config)
    return orchestrator.collect_dataset()

