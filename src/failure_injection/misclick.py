"""
MISCLICK injector (Action Mismatch).

Shifts click coordinates away from target to simulate misclick errors.
"""

import logging
import random
from typing import Tuple

from .injection_engine import FailureInjector, InjectionConfig
from ..offline_data.offline_schema import OfflineStep, OfflineTrajectory, AugmentedStep
from ..offline_data.image_preprocessor import shift_bbox, get_bbox_center

logger = logging.getLogger(__name__)


class MisclickInjector(FailureInjector):
    """
    Injects MISCLICK failures by shifting click coordinates.
    
    Method: Shift action coordinates away from target bbox
    
    Labels:
    - failure_type: action_mismatch
    - failure_subtype: WRONG_COORDINATES
    - recovery_strategy: BACKTRACK then CLICK_CORRECT_TARGET
    """
    
    @property
    def injection_type(self) -> str:
        return "MISCLICK"
    
    @property
    def failure_type(self) -> str:
        return "action_mismatch"
    
    @property
    def failure_subtype(self) -> str:
        return "WRONG_COORDINATES"
    
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if MISCLICK can be injected.
        
        Requires:
        - Action type is CLICK or HOVER
        - Valid target_bbox
        - Valid screenshots
        
        Args:
            step: Step to check
            
        Returns:
            True if injectable
        """
        if not step.is_valid:
            return False
        
        # Only inject on click/hover actions
        if step.action_type not in ["CLICK", "HOVER", "SELECT"]:
            return False
        
        if step.target_bbox is None:
            return False
        
        if step.state_before is None:
            return False
        
        return True
    
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject MISCLICK failure.
        
        Args:
            step: Original step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with shifted coordinates
        """
        # Get original target coordinates
        original_coords = get_bbox_center(step.target_bbox)
        
        # Compute misclick coordinates
        misclick_coords = self._compute_misclick_coords(
            original_coords,
            step.state_before.size
        )
        
        # Create modified action
        action_modified = {
            "action_type": step.action_type,
            "original_coords": original_coords,
            "misclick_coords": misclick_coords,
            "shift_distance": self._compute_distance(original_coords, misclick_coords)
        }
        
        # State screenshots remain the same (but action targeted wrong location)
        state_before_modified = step.state_before
        state_after_modified = step.state_after  # Shows result of misclick
        
        # Recovery: BACKTRACK then CLICK correct target
        recovery_strategy = "BACKTRACK"
        recovery_action = self._create_recovery_action(step, original_coords)
        recovery_success = self._determine_recovery_success()
        
        # Create augmented step
        augmented_step = self._create_augmented_step(
            original_step=step,
            execution_outcome="FAILURE",
            state_before_modified=state_before_modified,
            state_after_modified=state_after_modified,
            action_modified=action_modified,
            root_cause=f"Clicked at {misclick_coords} instead of target at {original_coords}",
            recovery_strategy=recovery_strategy,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            recovery_duration_ms=random.randint(1000, 3000) if recovery_success else 0
        )
        
        if recovery_success:
            self.success_count += 1
        
        logger.debug(
            f"MISCLICK injected: {step.task_id} step {step.step_number} "
            f"(shift={action_modified['shift_distance']:.0f}px, recovery={recovery_success})"
        )
        
        return augmented_step
    
    def _compute_misclick_coords(
        self, 
        target_coords: Tuple[int, int],
        image_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """
        Compute misclick coordinates by shifting from target.
        
        Args:
            target_coords: (x, y) of target center
            image_size: (width, height) of image
            
        Returns:
            (x, y) of misclick location
        """
        min_shift, max_shift = self.config.misclick_distance_range
        
        # Random shift in both directions
        shift_x = random.randint(min_shift, max_shift)
        shift_y = random.randint(min_shift, max_shift)
        
        # Random direction
        if random.random() < 0.5:
            shift_x *= -1
        if random.random() < 0.5:
            shift_y *= -1
        
        # Compute new coordinates
        new_x = target_coords[0] + shift_x
        new_y = target_coords[1] + shift_y
        
        # Clamp to image boundaries
        new_x = max(0, min(new_x, image_size[0] - 1))
        new_y = max(0, min(new_y, image_size[1] - 1))
        
        return (new_x, new_y)
    
    def _compute_distance(
        self, 
        coords1: Tuple[int, int], 
        coords2: Tuple[int, int]
    ) -> float:
        """Compute Euclidean distance between two coordinates."""
        return ((coords1[0] - coords2[0]) ** 2 + (coords1[1] - coords2[1]) ** 2) ** 0.5
    
    def _create_recovery_action(
        self, 
        step: OfflineStep,
        correct_coords: Tuple[int, int]
    ) -> dict:
        """
        Create recovery action: BACKTRACK then CLICK correct target.
        
        Args:
            step: Original step
            correct_coords: Correct target coordinates
            
        Returns:
            Recovery action dict
        """
        return {
            "method": "BACKTRACK",
            "steps": [
                {
                    "action_type": "NAVIGATE_BACK",
                    "description": "Undo misclick by navigating back"
                },
                {
                    "action_type": step.action_type,
                    "target_coords": correct_coords,
                    "target_uid": step.action_uid,
                    "description": f"Click correct target at {correct_coords}"
                }
            ],
            "total_steps": 2
        }
    
    def _determine_recovery_success(self) -> bool:
        """
        Determine if recovery succeeds.
        
        Returns:
            True if recovery succeeds
        """
        success_rate = self.config.recovery_success_rates.get("MISCLICK", 0.55)
        return random.random() < success_rate
