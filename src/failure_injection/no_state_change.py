"""
NO_STATE_CHANGE injector (Ineffective Action).

Duplicates state_before as state_after to simulate no visual change.
"""

import logging
import random

from .injection_engine import FailureInjector, InjectionConfig
from ..offline_data.offline_schema import OfflineStep, OfflineTrajectory, AugmentedStep
from ..offline_data.image_preprocessor import add_noise, compute_visual_metrics

logger = logging.getLogger(__name__)


class NoStateChangeInjector(FailureInjector):
    """
    Injects NO_STATE_CHANGE failures by making state_after identical to state_before.
    
    Method: Duplicate state_before as state_after (or add tiny imperceptible noise)
    
    Labels:
    - failure_type: state_no_change
    - failure_subtype: NO_VISUAL_RESPONSE
    - recovery_strategy: RETRY or ALTERNATIVE_ACTION
    """
    
    @property
    def injection_type(self) -> str:
        return "NO_STATE_CHANGE"
    
    @property
    def failure_type(self) -> str:
        return "state_no_change"
    
    @property
    def failure_subtype(self) -> str:
        return "NO_VISUAL_RESPONSE"
    
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if NO_STATE_CHANGE can be injected.
        
        Requires:
        - Valid state_before
        - Action should normally cause state change
        
        Args:
            step: Step to check
            
        Returns:
            True if injectable
        """
        if not step.is_valid:
            return False
        
        if step.state_before is None:
            return False
        
        # Can inject on most action types except navigation
        injectable_types = ["CLICK", "TYPE", "SELECT", "HOVER", "SCROLL"]
        if step.action_type not in injectable_types:
            return False
        
        return True
    
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject NO_STATE_CHANGE failure.
        
        Args:
            step: Original step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with no state change
        """
        # Decide whether to add imperceptible noise
        add_tiny_noise = random.random() < 0.3  # 30% of the time
        
        if add_tiny_noise:
            # Add very small noise to make it slightly different but unnoticeable
            state_after_modified = add_noise(step.state_before, epsilon=0.001)
        else:
            # Exact duplicate
            state_after_modified = step.state_before.copy()
        
        state_before_modified = step.state_before
        
        # Compute visual metrics (should be very high similarity)
        metrics = compute_visual_metrics(state_before_modified, state_after_modified)
        
        # URLs remain the same
        url_after_modified = step.url_before
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(step)
        recovery_action = self._create_recovery_action(step, recovery_strategy)
        recovery_success = self._determine_recovery_success()
        
        # Create augmented step
        augmented_step = self._create_augmented_step(
            original_step=step,
            execution_outcome="FAILURE",
            state_before_modified=state_before_modified,
            state_after_modified=state_after_modified,
            pixel_diff_modified=metrics["pixel_diff"],
            ssim_modified=metrics["ssim"],
            root_cause="Action had no visible effect on page state",
            recovery_strategy=recovery_strategy,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            recovery_duration_ms=random.randint(500, 2000) if recovery_success else 0
        )
        
        if recovery_success:
            self.success_count += 1
        
        logger.debug(
            f"NO_STATE_CHANGE injected: {step.task_id} step {step.step_number} "
            f"(ssim={metrics['ssim']:.3f}, recovery={recovery_strategy}, success={recovery_success})"
        )
        
        return augmented_step
    
    def _determine_recovery_strategy(self, step: OfflineStep) -> str:
        """
        Determine recovery strategy.
        
        Args:
            step: Original step
            
        Returns:
            Recovery strategy name
        """
        # 60% RETRY, 40% ALTERNATIVE_ACTION
        if random.random() < 0.6:
            return "RETRY"
        else:
            return "ALTERNATIVE_ACTION"
    
    def _create_recovery_action(
        self, 
        step: OfflineStep,
        recovery_strategy: str
    ) -> dict:
        """
        Create recovery action.
        
        Args:
            step: Original step
            recovery_strategy: Strategy name
            
        Returns:
            Recovery action dict
        """
        if recovery_strategy == "RETRY":
            return {
                "method": "RETRY",
                "steps": [
                    {
                        "action_type": "WAIT",
                        "duration_ms": random.randint(1000, 3000),
                        "description": "Wait for page to respond"
                    },
                    {
                        "action_type": step.action_type,
                        "target_uid": step.action_uid,
                        "description": f"Retry {step.action_type} action"
                    }
                ],
                "total_steps": 2
            }
        
        elif recovery_strategy == "ALTERNATIVE_ACTION":
            # Try a different action type
            alternative_action = self._suggest_alternative_action(step.action_type)
            
            return {
                "method": "ALTERNATIVE_ACTION",
                "steps": [
                    {
                        "action_type": alternative_action,
                        "target_uid": step.action_uid,
                        "description": f"Try alternative action: {alternative_action}"
                    }
                ],
                "total_steps": 1
            }
        
        else:
            return {
                "method": "UNKNOWN",
                "description": "No recovery defined"
            }
    
    def _suggest_alternative_action(self, original_action: str) -> str:
        """
        Suggest alternative action type.
        
        Args:
            original_action: Original action that had no effect
            
        Returns:
            Alternative action type
        """
        alternatives = {
            "CLICK": "HOVER",
            "HOVER": "CLICK",
            "TYPE": "SELECT",
            "SELECT": "TYPE",
            "SCROLL": "CLICK"
        }
        
        return alternatives.get(original_action, "CLICK")
    
    def _determine_recovery_success(self) -> bool:
        """
        Determine if recovery succeeds.
        
        Returns:
            True if recovery succeeds
        """
        success_rate = self.config.recovery_success_rates.get("NO_STATE_CHANGE", 0.45)
        return random.random() < success_rate
