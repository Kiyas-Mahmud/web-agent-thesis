"""
Reflection Annotator

Main class that orchestrates reflection annotation:
- Estimates confidence before and after actions
- Generates reflection texts
- Detects memory signals
- Creates introspection metadata
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json

try:
    from .reflection_schema import (
        ReflectionAnnotation,
        ReflectionConfig,
        DEFAULT_REFLECTION_CONFIG,
        MemoryType,
        ReasoningType,
        UncertaintySource,
        IntrospectionMetadata,
        create_reflection_annotation,
    )
    from .confidence_estimator import ConfidenceEstimator, ConfidenceFactors
    from .reflection_generator import ReflectionGenerator
    from .memory_signals import MemorySignalDetector
except ImportError:
    from reflection_annotation.reflection_schema import (
        ReflectionAnnotation,
        ReflectionConfig,
        DEFAULT_REFLECTION_CONFIG,
        MemoryType,
        ReasoningType,
        UncertaintySource,
        IntrospectionMetadata,
        create_reflection_annotation,
    )
    from reflection_annotation.confidence_estimator import ConfidenceEstimator, ConfidenceFactors
    from reflection_annotation.reflection_generator import ReflectionGenerator
    from reflection_annotation.memory_signals import MemorySignalDetector


class ReflectionAnnotator:
    """Main reflection annotation orchestrator.
    
    Combines confidence estimation, reflection generation, and memory signal detection
    to create comprehensive introspective annotations.
    """
    
    def __init__(self, config: Optional[ReflectionConfig] = None):
        """Initialize reflection annotator.
        
        Args:
            config: Reflection configuration
        """
        self.config = config or DEFAULT_REFLECTION_CONFIG
        
        # Initialize components
        self.confidence_estimator = ConfidenceEstimator(config)
        self.reflection_generator = ReflectionGenerator(config)
        self.memory_detector = MemorySignalDetector(config)
        
        # Statistics
        self.total_annotations = 0
        self.annotations_by_type: Dict[MemoryType, int] = {
            mem_type: 0 for mem_type in MemoryType
        }
    
    def annotate_step(
        self,
        step_id: int,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]] = None,
        recovery_info: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ReflectionAnnotation:
        """Create full reflection annotation for a step.
        
        Args:
            step_id: Step index in trajectory
            action: Action that was performed
            outcome: Outcome information
            failure_info: Failure detection info (from Task-04)
            recovery_info: Recovery attempt info (from Task-05)
            metrics: Visual/state metrics (from Task-03)
            
        Returns:
            Complete reflection annotation
        """
        # Build confidence factors
        confidence_factors = self._build_confidence_factors(
            action, outcome, failure_info, recovery_info, metrics
        )
        
        # Estimate confidence before action
        confidence_before = self.confidence_estimator.estimate_before_action(confidence_factors)
        
        # Estimate confidence after action
        confidence_after = self.confidence_estimator.estimate_after_action(
            confidence_factors, confidence_before
        )
        
        # Update action history
        action_success = outcome.get("success", False)
        self.confidence_estimator.update_history(action_success)
        
        # Generate reflection text
        reflection_text = self.reflection_generator.generate_reflection(
            action, outcome, failure_info, recovery_info, metrics
        )
        
        # Detect memory signal
        memory_update_flag, memory_type = self.memory_detector.detect_memory_signal(
            confidence_before, confidence_after, failure_info, recovery_info, outcome
        )
        
        # Create introspection metadata
        introspection_metadata = self._create_introspection_metadata(
            action, outcome, failure_info, recovery_info, confidence_before, confidence_after
        )
        
        # Create annotation
        # Create annotation directly
        annotation = ReflectionAnnotation(
            step_id=step_id,
            agent_confidence_before=confidence_before,
            agent_confidence_after=confidence_after,
            confidence_delta=confidence_after - confidence_before,
            reflection_text=reflection_text,
            memory_update_flag=memory_update_flag,
            memory_type=memory_type,
            introspection_metadata=introspection_metadata,
        )
        
        # Update statistics
        self.total_annotations += 1
        self.annotations_by_type[memory_type] += 1
        
        return annotation
    
    def annotate_trajectory(
        self,
        trajectory: Dict[str, Any],
        failure_labels: Optional[List[Dict[str, Any]]] = None,
        recovery_attempts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[ReflectionAnnotation]:
        """Annotate all steps in a trajectory.
        
        Args:
            trajectory: Full trajectory with steps
            failure_labels: List of failure labels (from Task-04)
            recovery_attempts: List of recovery attempts (from Task-05)
            
        Returns:
            List of reflection annotations for each step
        """
        steps = trajectory.get("steps", [])
        
        # Create lookup by step_id
        failure_lookup = {}
        if failure_labels:
            for failure in failure_labels:
                step_id = failure.get("step_id")
                if step_id is not None:
                    failure_lookup[step_id] = failure
        
        recovery_lookup = {}
        if recovery_attempts:
            for recovery in recovery_attempts:
                step_id = recovery.get("step_id")
                if step_id is not None:
                    recovery_lookup[step_id] = recovery
        
        # Annotate each step
        annotations = []
        for i, step in enumerate(steps):
            step_id = step.get("step_id", i)
            
            # Get associated failure and recovery info
            failure_info = failure_lookup.get(step_id)
            recovery_info = recovery_lookup.get(step_id)
            
            # Extract action, outcome, and metrics from nested structure
            action_data = step.get("action", {})
            result_data = step.get("result", {})
            
            action = {
                "type": action_data.get("action_type", ""),
                "target": action_data.get("target", action_data.get("url", "element")),
                "text": action_data.get("text", ""),
                "value": action_data.get("value", ""),
            }
            
            outcome = {
                "success": result_data.get("success", True),
                "timeout": result_data.get("timeout", False),
                "loop_detected": result_data.get("loop_detected", False),
                "state_changed": result_data.get("state_changed", False),
            }
            
            metrics = step.get("metrics", {})
            
            # Create annotation
            annotation = self.annotate_step(
                step_id, action, outcome, failure_info, recovery_info, metrics
            )
            annotations.append(annotation)
        
        return annotations
    
    def save_annotations(
        self,
        annotations: List[ReflectionAnnotation],
        output_file: Path,
    ) -> None:
        """Save annotations to JSONL file.
        
        Args:
            annotations: List of reflection annotations
            output_file: Output file path
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            for annotation in annotations:
                # Convert to dict
                annotation_dict = annotation.model_dump()
                # Write as JSON line
                f.write(json.dumps(annotation_dict) + "\n")
    
    def load_annotations(self, input_file: Path) -> List[ReflectionAnnotation]:
        """Load annotations from JSONL file.
        
        Args:
            input_file: Input file path
            
        Returns:
            List of reflection annotations
        """
        annotations = []
        
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON
                annotation_dict = json.loads(line)
                
                # Create annotation object
                annotation = ReflectionAnnotation(**annotation_dict)
                annotations.append(annotation)
        
        return annotations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get annotation statistics.
        
        Returns:
            Statistics dictionary
        """
        # Get component statistics
        confidence_stats = self.confidence_estimator.get_statistics()
        memory_stats = self.memory_detector.get_statistics()
        
        # Calculate distribution
        memory_distribution = {
            mem_type.value: count
            for mem_type, count in self.annotations_by_type.items()
            if count > 0
        }
        
        return {
            "total_annotations": self.total_annotations,
            "memory_type_distribution": memory_distribution,
            "confidence_statistics": confidence_stats,
            "memory_statistics": memory_stats,
        }
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.total_annotations = 0
        self.annotations_by_type = {mem_type: 0 for mem_type in MemoryType}
        self.confidence_estimator.reset_history()
        self.memory_detector.reset_statistics()
    
    def _build_confidence_factors(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]],
        recovery_info: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]],
    ) -> ConfidenceFactors:
        """Build confidence factors from available information.
        
        Args:
            action: Action information
            outcome: Outcome information
            failure_info: Failure detection info
            recovery_info: Recovery attempt info
            metrics: Visual/state metrics
            
        Returns:
            ConfidenceFactors object
        """
        # Extract element detection info
        element_found = action.get("element_found", True)
        element_visibility = action.get("element_visibility", 1.0)
        
        # Extract page state
        page_loaded = outcome.get("page_loaded", True)
        page_stable = outcome.get("page_stable", True)
        page_complexity = metrics.get("page_complexity", 0.5) if metrics else 0.5
        
        # Extract metrics
        visual_change = False
        state_change = False
        if metrics:
            visual_metrics = metrics.get("visual", {})
            visual_change = visual_metrics.get("pixel_diff", 0) > 0.05
            
            state_metrics = metrics.get("state_hash", {})
            state_change = state_metrics.get("changed", False)
        
        # Extract failure info
        failure_type = None
        failure_severity = 0
        failure_confidence = 0
        if failure_info:
            failure_type = failure_info.get("failure_type")
            if failure_type and failure_type != "none":
                failure_severity = failure_info.get("severity", 0.5)
                failure_confidence = failure_info.get("confidence", 0.5)
        
        # Extract recovery info
        recovery_attempted = False
        recovery_success = False
        recovery_strategy = None
        if recovery_info:
            recovery_attempted = recovery_info.get("attempted", False)
            recovery_success = recovery_info.get("success", False)
            recovery_strategy = recovery_info.get("strategy")
        
        # Extract timeouts and loops
        action_timeout = outcome.get("timeout", False)
        loop_detected = outcome.get("loop_detected", False)
        
        # Build factors
        return ConfidenceFactors(
            element_found=element_found,
            element_visibility=element_visibility,
            selector_confidence=0.9 if element_found else 0.1,
            page_complexity=page_complexity,
            page_loaded=page_loaded,
            page_stable=page_stable,
            visual_change_detected=visual_change,
            state_change_detected=state_change,
            action_timeout=action_timeout,
            loop_detected=loop_detected,
            failure_type=failure_type,
            failure_severity=failure_severity,
            failure_confidence=failure_confidence,
            recovery_attempted=recovery_attempted,
            recovery_success=recovery_success,
            recovery_strategy=recovery_strategy,
        )
    
    def _create_introspection_metadata(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]],
        recovery_info: Optional[Dict[str, Any]],
        confidence_before: float,
        confidence_after: float,
    ) -> IntrospectionMetadata:
        """Create introspection metadata.
        
        Args:
            action: Action information
            outcome: Outcome information
            failure_info: Failure detection info
            recovery_info: Recovery attempt info
            confidence_before: Confidence before action
            confidence_after: Confidence after action
            
        Returns:
            IntrospectionMetadata object
        """
        # Determine reasoning type
        if recovery_info and recovery_info.get("attempted"):
            reasoning_type = ReasoningType.RECOVERY
        elif failure_info and failure_info.get("failure_type") not in [None, "none"]:
            reasoning_type = ReasoningType.DIAGNOSIS
        elif outcome.get("success", False):
            reasoning_type = ReasoningType.EXECUTION
        else:
            reasoning_type = ReasoningType.EVALUATION
        
        # Determine uncertainty source
        uncertainty_source = UncertaintySource.NONE
        if confidence_before < 0.5 or confidence_after < 0.5:
            # Determine primary source of uncertainty
            if not action.get("element_found", True):
                uncertainty_source = UncertaintySource.ELEMENT_DETECTION
            elif outcome.get("timeout", False):
                uncertainty_source = UncertaintySource.TIMING
            elif not outcome.get("page_stable", True):
                uncertainty_source = UncertaintySource.PAGE_STATE
            elif failure_info:
                uncertainty_source = UncertaintySource.ACTION_EFFECT
            else:
                uncertainty_source = UncertaintySource.GOAL_ALIGNMENT
        
        # Determine learning signal strength
        confidence_delta = abs(confidence_after - confidence_before)
        if confidence_delta > 0.4:
            learning_signal = "strong"
        elif confidence_delta > 0.2:
            learning_signal = "moderate"
        elif confidence_delta > 0.1:
            learning_signal = "weak"
        else:
            learning_signal = "none"
        
        # Collect context factors
        context_factors = {}
        if failure_info:
            context_factors["failure_type"] = failure_info.get('failure_type', 'unknown')
            context_factors["failure_severity"] = failure_info.get('severity', 0.0)
        if recovery_info and recovery_info.get("attempted"):
            context_factors["recovery_strategy"] = recovery_info.get('strategy', 'unknown')
            context_factors["recovery_success"] = recovery_info.get('success', False)
        if outcome.get("timeout"):
            context_factors["timeout"] = True
        if outcome.get("loop_detected"):
            context_factors["loop_detected"] = True
        
        return IntrospectionMetadata(
            reasoning_type=reasoning_type,
            uncertainty_source=uncertainty_source,
            learning_signal=learning_signal,
            alternative_hypotheses=[],  # Could be enhanced
            context_factors=context_factors,
        )


def batch_annotate_trajectories(
    input_dir: Path,
    output_dir: Path,
    failure_dir: Optional[Path] = None,
    recovery_dir: Optional[Path] = None,
    config: Optional[ReflectionConfig] = None,
) -> Dict[str, Any]:
    """Batch annotate multiple trajectories.
    
    Args:
        input_dir: Directory with trajectory JSONL files
        output_dir: Directory for output reflection annotations
        failure_dir: Directory with failure labels (optional)
        recovery_dir: Directory with recovery attempts (optional)
        config: Reflection configuration
        
    Returns:
        Statistics about annotation process
    """
    annotator = ReflectionAnnotator(config)
    
    # Get all trajectory files
    trajectory_files = list(input_dir.glob("*.jsonl"))
    
    total_trajectories = 0
    total_steps = 0
    
    for traj_file in trajectory_files:
        # Load trajectory
        with open(traj_file, "r", encoding="utf-8") as f:
            trajectory = json.load(f)
        
        # Load failure labels if available
        failure_labels = None
        if failure_dir:
            failure_file = failure_dir / traj_file.name
            if failure_file.exists():
                with open(failure_file, "r", encoding="utf-8") as f:
                    failure_labels = [json.loads(line) for line in f]
        
        # Load recovery attempts if available
        recovery_attempts = None
        if recovery_dir:
            recovery_file = recovery_dir / traj_file.name
            if recovery_file.exists():
                with open(recovery_file, "r", encoding="utf-8") as f:
                    recovery_attempts = [json.loads(line) for line in f]
        
        # Annotate trajectory
        annotations = annotator.annotate_trajectory(
            trajectory, failure_labels, recovery_attempts
        )
        
        # Save annotations
        output_file = output_dir / traj_file.name
        annotator.save_annotations(annotations, output_file)
        
        total_trajectories += 1
        total_steps += len(annotations)
    
    # Get statistics
    stats = annotator.get_statistics()
    stats["total_trajectories"] = total_trajectories
    stats["total_steps"] = total_steps
    
    return stats
