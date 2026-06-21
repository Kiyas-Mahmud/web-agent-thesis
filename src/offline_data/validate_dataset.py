"""
Dataset validation and integrity checks.

Validates:
- Screenshot availability
- Bounding box completeness
- Action annotation quality
- Trajectory continuity
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from .offline_schema import OfflineTrajectory, OfflineStep
from .image_preprocessor import compute_visual_metrics

logger = logging.getLogger(__name__)


class DatasetValidator:
    """
    Validates offline dataset integrity and quality.
    """
    
    def __init__(self):
        self.validation_results = {
            "total_trajectories": 0,
            "total_steps": 0,
            "valid_trajectories": 0,
            "valid_steps": 0,
            "errors": []
        }
    
    def validate_trajectories(
        self, 
        trajectories: List[OfflineTrajectory]
    ) -> Dict[str, Any]:
        """
        Validate a list of trajectories.
        
        Args:
            trajectories: List of OfflineTrajectory objects
            
        Returns:
            Validation report dict
        """
        logger.info(f"Validating {len(trajectories)} trajectories...")
        
        self.validation_results["total_trajectories"] = len(trajectories)
        
        for traj in trajectories:
            is_valid = self._validate_trajectory(traj)
            if is_valid:
                self.validation_results["valid_trajectories"] += 1
        
        # Compute summary statistics
        total_steps = self.validation_results["total_steps"]
        valid_steps = self.validation_results["valid_steps"]
        
        self.validation_results["step_validity_rate"] = (
            valid_steps / total_steps * 100 if total_steps > 0 else 0
        )
        
        self.validation_results["trajectory_validity_rate"] = (
            self.validation_results["valid_trajectories"] / 
            len(trajectories) * 100 if trajectories else 0
        )
        
        # Summarize error types
        error_counts = {}
        for error in self.validation_results["errors"]:
            error_type = error.get("type", "unknown")
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        self.validation_results["error_summary"] = error_counts
        
        logger.info(f"✅ Validation complete:")
        logger.info(f"  Trajectory validity: {self.validation_results['trajectory_validity_rate']:.1f}%")
        logger.info(f"  Step validity: {self.validation_results['step_validity_rate']:.1f}%")
        
        return self.validation_results
    
    def _validate_trajectory(self, trajectory: OfflineTrajectory) -> bool:
        """
        Validate a single trajectory.
        
        Args:
            trajectory: OfflineTrajectory object
            
        Returns:
            True if valid, False otherwise
        """
        is_valid = True
        
        # Check metadata
        if not trajectory.task_id:
            self._add_error("missing_task_id", trajectory.task_id, -1)
            is_valid = False
        
        if not trajectory.confirmed_task:
            self._add_error("missing_task_description", trajectory.task_id, -1)
        
        # Check steps
        if len(trajectory.steps) == 0:
            self._add_error("empty_trajectory", trajectory.task_id, -1)
            is_valid = False
        
        # Validate each step
        for step in trajectory.steps:
            step_valid = self._validate_step(step, trajectory.task_id)
            self.validation_results["total_steps"] += 1
            
            if step_valid:
                self.validation_results["valid_steps"] += 1
            else:
                is_valid = False
        
        return is_valid
    
    def _validate_step(self, step: OfflineStep, task_id: str) -> bool:
        """
        Validate a single step.
        
        Args:
            step: OfflineStep object
            task_id: Task ID for error reporting
            
        Returns:
            True if valid, False otherwise
        """
        is_valid = True
        
        # Check screenshots
        if step.state_before is None:
            self._add_error("missing_state_before", task_id, step.step_number)
            is_valid = False
        
        if step.state_after is None:
            self._add_error("missing_state_after", task_id, step.step_number)
            is_valid = False
        
        # Check bounding box
        if step.target_bbox is None:
            self._add_error("missing_target_bbox", task_id, step.step_number)
            is_valid = False
        else:
            # Validate bbox coordinates
            bbox = step.target_bbox
            if bbox["width"] <= 0 or bbox["height"] <= 0:
                self._add_error("invalid_bbox_dimensions", task_id, step.step_number)
                is_valid = False
        
        # Check action
        if not step.action_type or step.action_type == "UNKNOWN":
            self._add_error("missing_action_type", task_id, step.step_number)
            is_valid = False
        
        if not step.action_uid:
            self._add_error("missing_action_uid", task_id, step.step_number)
        
        # Compute visual metrics if both screenshots available
        if step.state_before and step.state_after:
            try:
                metrics = compute_visual_metrics(step.state_before, step.state_after)
                step.pixel_diff = metrics["pixel_diff"]
                step.ssim = metrics["ssim"]
            except Exception as e:
                self._add_error("visual_metrics_computation_failed", task_id, step.step_number, str(e))
        
        return is_valid
    
    def _add_error(
        self, 
        error_type: str, 
        task_id: str, 
        step_number: int,
        details: str = ""
    ):
        """Add error to validation results."""
        self.validation_results["errors"].append({
            "type": error_type,
            "task_id": task_id,
            "step_number": step_number,
            "details": details
        })
    
    def get_quality_report(self) -> str:
        """
        Generate human-readable quality report.
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("="*60)
        report.append("Dataset Quality Report")
        report.append("="*60)
        
        report.append(f"\nTrajectories:")
        report.append(f"  Total: {self.validation_results['total_trajectories']}")
        report.append(f"  Valid: {self.validation_results['valid_trajectories']}")
        report.append(f"  Validity Rate: {self.validation_results.get('trajectory_validity_rate', 0):.1f}%")
        
        report.append(f"\nSteps:")
        report.append(f"  Total: {self.validation_results['total_steps']}")
        report.append(f"  Valid: {self.validation_results['valid_steps']}")
        report.append(f"  Validity Rate: {self.validation_results.get('step_validity_rate', 0):.1f}%")
        
        report.append(f"\nError Summary:")
        error_summary = self.validation_results.get("error_summary", {})
        if error_summary:
            for error_type, count in sorted(error_summary.items(), key=lambda x: -x[1])[:10]:
                report.append(f"  {error_type}: {count}")
        else:
            report.append("  No errors found")
        
        report.append("="*60)
        
        return "\n".join(report)


def check_dataset_balance(trajectories: List[OfflineTrajectory]) -> Dict[str, Any]:
    """
    Check dataset balance across domains and websites.
    
    Args:
        trajectories: List of trajectories
        
    Returns:
        Balance statistics
    """
    domain_counts = {}
    website_counts = {}
    step_counts = []
    
    for traj in trajectories:
        domain_counts[traj.domain] = domain_counts.get(traj.domain, 0) + 1
        website_counts[traj.website] = website_counts.get(traj.website, 0) + 1
        step_counts.append(traj.num_steps)
    
    return {
        "num_domains": len(domain_counts),
        "num_websites": len(website_counts),
        "domain_distribution": domain_counts,
        "website_distribution": website_counts,
        "avg_steps_per_trajectory": sum(step_counts) / len(step_counts) if step_counts else 0,
        "min_steps": min(step_counts) if step_counts else 0,
        "max_steps": max(step_counts) if step_counts else 0
    }
