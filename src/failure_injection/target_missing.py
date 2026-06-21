"""
TARGET_MISSING injector (Perception Error).

Masks the target element in the screenshot to simulate perception failures.
"""

import logging
from typing import Optional
import random

from .injection_engine import FailureInjector, InjectionConfig
from ..offline_data.offline_schema import OfflineStep, OfflineTrajectory, AugmentedStep
from ..offline_data.image_preprocessor import mask_bbox, find_alternative_target

logger = logging.getLogger(__name__)


class TargetMissingInjector(FailureInjector):
    """
    Injects TARGET_MISSING failures by masking the target element.
    
    Method 1: Mask target region in screenshot (blur/black/noise)
    Method 2: Remove target bbox from annotations
    
    Labels:
    - failure_type: perception_error
    - failure_subtype: ELEMENT_MISSING
    - recovery_strategy: ALTERNATIVE_TARGET or SCROLL_AND_RETRY
    """
    
    @property
    def injection_type(self) -> str:
        return "TARGET_MISSING"
    
    @property
    def failure_type(self) -> str:
        return "perception_error"
    
    @property
    def failure_subtype(self) -> str:
        return "ELEMENT_MISSING"
    
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if TARGET_MISSING can be injected.
        
        Requires:
        - Valid state_before screenshot
        - Valid target_bbox
        
        Args:
            step: Step to check
            
        Returns:
            True if injectable
        """
        if not step.is_valid:
            return False
        
        if step.state_before is None:
            return False
        
        if step.target_bbox is None:
            return False
        
        return True
    
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject TARGET_MISSING failure.
        
        Args:
            step: Original step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with masked target
        """
        # Choose masking method
        mask_methods = ["blur", "black", "noise"]
        mask_type = random.choice(mask_methods)
        
        # Mask the target in state_before
        state_before_modified = mask_bbox(
            step.state_before,
            step.target_bbox,
            mask_type=mask_type
        )
        
        # state_after remains unmodified (still shows result of attempted action)
        state_after_modified = step.state_after
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(step)
        
        # Create recovery action
        recovery_action = self._create_recovery_action(step, recovery_strategy)
        
        # Determine recovery success
        recovery_success = self._determine_recovery_success()
        
        # Create augmented step
        augmented_step = self._create_augmented_step(
            original_step=step,
            execution_outcome="FAILURE",
            state_before_modified=state_before_modified,
            state_after_modified=state_after_modified,
            root_cause="Target element masked or missing from view",
            recovery_strategy=recovery_strategy,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            recovery_duration_ms=random.randint(500, 2000) if recovery_success else 0
        )
        
        if recovery_success:
            self.success_count += 1
        
        logger.debug(
            f"TARGET_MISSING injected: {step.task_id} step {step.step_number} "
            f"(mask={mask_type}, recovery={recovery_strategy}, success={recovery_success})"
        )
        
        return augmented_step
    
    def _determine_recovery_strategy(self, step: OfflineStep) -> str:
        """
        Determine appropriate recovery strategy.
        
        Args:
            step: Original step
            
        Returns:
            Recovery strategy name
        """
        # If alternative targets available, use ALTERNATIVE_TARGET
        if step.candidate_bboxes and len(step.candidate_bboxes) > 1:
            # 70% chance to use alternative target
            if random.random() < 0.7:
                return "ALTERNATIVE_TARGET"
        
        # Otherwise, use SCROLL_AND_RETRY
        return "SCROLL_AND_RETRY"
    
    def _create_recovery_action(
        self, 
        step: OfflineStep, 
        recovery_strategy: str
    ) -> dict:
        """
        Create recovery action details.
        
        Args:
            step: Original step
            recovery_strategy: Strategy name
            
        Returns:
            Recovery action dict
        """
        if recovery_strategy == "ALTERNATIVE_TARGET":
            # Find alternative target from candidates
            alternative = find_alternative_target(
                step.target_bbox,
                step.candidate_bboxes,
                avoid_overlap=True
            )
            
            return {
                "method": "ALTERNATIVE_TARGET",
                "action_type": step.action_type,
                "target_uid": alternative.get("uid", "") if alternative else "",
                "target_bbox": alternative if alternative else None,
                "description": f"Click alternative element instead of masked target"
            }
        
        elif recovery_strategy == "SCROLL_AND_RETRY":
            return {
                "method": "SCROLL_AND_RETRY",
                "action_type": "SCROLL",
                "scroll_direction": random.choice(["DOWN", "UP"]),
                "scroll_amount": random.randint(100, 300),
                "description": "Scroll to reveal masked element, then retry"
            }
        
        else:
            return {
                "method": "UNKNOWN",
                "description": "No recovery action defined"
            }
    
    def _determine_recovery_success(self) -> bool:
        """
        Determine if recovery succeeds.
        
        Uses configured recovery success rate for TARGET_MISSING.
        
        Returns:
            True if recovery succeeds
        """
        success_rate = self.config.recovery_success_rates.get("TARGET_MISSING", 0.65)
        return random.random() < success_rate
