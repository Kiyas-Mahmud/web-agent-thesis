"""
WRONG_OPERATION injector (Reasoning Error).

Swaps action types to simulate reasoning failures.
"""

import logging
import random

from .injection_engine import FailureInjector, InjectionConfig
from ..offline_data.offline_schema import OfflineStep, OfflineTrajectory, AugmentedStep
from ..offline_data.annotation_processor import swap_action_type

logger = logging.getLogger(__name__)


class WrongOperationInjector(FailureInjector):
    """
    Injects WRONG_OPERATION failures by swapping action types.
    
    Method: Change action_type (e.g., CLICK -> TYPE, TYPE -> CLICK)
    
    Labels:
    - failure_type: reasoning_error
    - failure_subtype: WRONG_ACTION_TYPE
    - recovery_strategy: REPLAN then correct action
    """
    
    @property
    def injection_type(self) -> str:
        return "WRONG_OPERATION"
    
    @property
    def failure_type(self) -> str:
        return "reasoning_error"
    
    @property
    def failure_subtype(self) -> str:
        return "WRONG_ACTION_TYPE"
    
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if WRONG_OPERATION can be injected.
        
        Requires:
        - Valid action_type (not UNKNOWN)
        - Swappable action type
        
        Args:
            step: Step to check
            
        Returns:
            True if injectable
        """
        if not step.is_valid:
            return False
        
        if not step.action_type or step.action_type == "UNKNOWN":
            return False
        
        # Only inject on swappable action types
        swappable_types = ["CLICK", "TYPE", "SELECT", "HOVER", "SCROLL"]
        if step.action_type not in swappable_types:
            return False
        
        return True
    
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject WRONG_OPERATION failure.
        
        Args:
            step: Original step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with swapped action type
        """
        # Swap action type
        original_action_type = step.action_type
        swapped_action_type = swap_action_type(original_action_type)
        
        # Create modified action
        action_modified = {
            "original_action_type": original_action_type,
            "swapped_action_type": swapped_action_type,
            "action_target": step.action_target,
            "action_uid": step.action_uid
        }
        
        # Determine what text to use if swapped to TYPE
        if swapped_action_type == "TYPE":
            action_modified["type_text"] = self._generate_dummy_text()
        
        # Screenshots remain the same
        state_before_modified = step.state_before
        state_after_modified = step.state_after
        
        # Recovery: REPLAN then do correct action
        recovery_strategy = "REPLAN"
        recovery_action = self._create_recovery_action(step, original_action_type)
        recovery_success = self._determine_recovery_success()
        
        # Create augmented step
        augmented_step = self._create_augmented_step(
            original_step=step,
            execution_outcome="FAILURE",
            state_before_modified=state_before_modified,
            state_after_modified=state_after_modified,
            action_modified=action_modified,
            root_cause=f"Wrong action: used {swapped_action_type} instead of {original_action_type}",
            recovery_strategy=recovery_strategy,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            recovery_duration_ms=random.randint(800, 2500) if recovery_success else 0
        )
        
        if recovery_success:
            self.success_count += 1
        
        logger.debug(
            f"WRONG_OPERATION injected: {step.task_id} step {step.step_number} "
            f"({original_action_type} -> {swapped_action_type}, recovery={recovery_success})"
        )
        
        return augmented_step
    
    def _generate_dummy_text(self) -> str:
        """
        Generate dummy text for TYPE actions.
        
        Returns:
            Random dummy text
        """
        dummy_texts = [
            "test",
            "dummy",
            "wrong input",
            "abc123",
            "example"
        ]
        return random.choice(dummy_texts)
    
    def _create_recovery_action(
        self, 
        step: OfflineStep,
        correct_action_type: str
    ) -> dict:
        """
        Create recovery action: REPLAN then do correct action.
        
        Args:
            step: Original step
            correct_action_type: The correct action type
            
        Returns:
            Recovery action dict
        """
        return {
            "method": "REPLAN",
            "steps": [
                {
                    "action_type": "REPLAN",
                    "description": "Re-evaluate task context and determine correct action"
                },
                {
                    "action_type": correct_action_type,
                    "target_uid": step.action_uid,
                    "target": step.action_target,
                    "description": f"Execute correct action: {correct_action_type}"
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
        success_rate = self.config.recovery_success_rates.get("WRONG_OPERATION", 0.60)
        return random.random() < success_rate
