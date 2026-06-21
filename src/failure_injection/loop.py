"""
LOOP injector (Repetitive Behavior).

Repeats the same state multiple times to simulate loop detection.
"""

import logging
import random
from typing import List

from .injection_engine import FailureInjector, InjectionConfig
from ..offline_data.offline_schema import OfflineStep, OfflineTrajectory, AugmentedStep

logger = logging.getLogger(__name__)


class LoopInjector(FailureInjector):
    """
    Injects LOOP failures by repeating the same state.
    
    Method: Make state_after equal to a previous state (creating a loop pattern)
    
    Labels:
    - failure_type: loop_detected
    - failure_subtype: STATE_LOOP or URL_LOOP
    - recovery_strategy: BACKTRACK_TO_LAST_GOOD_STATE
    """
    
    @property
    def injection_type(self) -> str:
        return "LOOP"
    
    @property
    def failure_type(self) -> str:
        return "loop_detected"
    
    @property
    def failure_subtype(self) -> str:
        return "STATE_LOOP"
    
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check if LOOP can be injected.
        
        Requires:
        - Valid state_before and state_after
        - Not the first few steps (need history to create loop)
        
        Args:
            step: Step to check
            
        Returns:
            True if injectable
        """
        if not step.is_valid:
            return False
        
        if step.state_before is None or step.state_after is None:
            return False
        
        # Need at least 2 previous steps to create meaningful loop
        if step.step_number < 2:
            return False
        
        return True
    
    def inject(
        self, 
        step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> AugmentedStep:
        """
        Inject LOOP failure by detecting or creating stuck UI state.
        
        Uses SSIM to detect if state didn't change (natural loop),
        or forces a loop by making state_after identical to state_before.
        
        Args:
            step: Original step
            trajectory: Full trajectory context
            
        Returns:
            AugmentedStep with loop pattern
        """
        from ..offline_data.image_preprocessor import compute_ssim
        
        # Calculate similarity between before and after
        ssim_score = compute_ssim(step.state_before, step.state_after)
        
        # Determine if this is a natural loop or we need to force it
        if ssim_score > 0.95:
            # Natural loop detected - state barely changed
            loop_type = "natural"
            state_after_modified = step.state_after  # Keep as is
        else:
            # Force loop - make state_after identical to state_before
            loop_type = "injected"
            state_after_modified = step.state_before.copy()
            ssim_score = 1.0  # Perfect loop after forcing
        
        state_before_modified = step.state_before
        
        # Check for repetition pattern in trajectory history
        similar_actions = self._find_similar_actions(step, trajectory)
        repetition_count = len(similar_actions)
        
        # Determine recovery strategy based on repetition
        if repetition_count >= 2:
            # Detected repetitive pattern - need different approach
            recovery_strategy = "break_loop_try_different_approach"
            root_cause = f"Agent stuck in loop: repeated same action {repetition_count} times"
        else:
            # Single loop - might be timing issue
            recovery_strategy = "wait_and_retry"
            root_cause = "Page not responding - no state change detected"
        
        # Create recovery action
        recovery_action = {
            "action_type": "BACKTRACK_AND_RETRY",
            "backtrack_steps": min(3, repetition_count + 1),
            "retry_with_delay": True,
            "alternative_approach": repetition_count >= 2
        }
        
        # Determine recovery success
        recovery_success = self._determine_recovery_success()
        
        # Create augmented step matching the AugmentedStep schema
        augmented_step = AugmentedStep(
            original_step=step,
            is_augmented=True,
            injection_type="LOOP",
            state_before_modified=state_before_modified,
            state_after_modified=state_after_modified,
            action_modified=None,
            bbox_modified=None,
            failure_type="loop_detected",
            failure_subtype="STATE_LOOP",
            failure_confidence=0.75,
            root_cause=root_cause,
            recovery_strategy=recovery_strategy,
            recovery_action=recovery_action,
            recovery_success=recovery_success,
            recovery_duration_ms=random.randint(1500, 3000) if recovery_success else 0,
            execution_outcome="FAILURE",
            injection_config={
                "loop_type": loop_type,
                "ssim_score": float(ssim_score),
                "repetition_count": repetition_count,
                "similar_action_steps": [s.step_number for s in similar_actions[:3]]
            }
        )
        
        if recovery_success:
            self.success_count += 1
        
        logger.debug(
            f"LOOP injected: {step.task_id} step {step.step_number} "
            f"(type={loop_type}, ssim={ssim_score:.3f}, repetitions={repetition_count}, recovery={recovery_success})"
        )
        
        return augmented_step
    
    def _find_similar_actions(
        self, 
        current_step: OfflineStep,
        trajectory: OfflineTrajectory
    ) -> List[OfflineStep]:
        """
        Find similar actions in recent history to detect repetition patterns.
        
        Args:
            current_step: Current step being injected
            trajectory: Full trajectory
            
        Returns:
            List of similar previous steps
        """
        similar = []
        
        # Look at last 5 steps
        lookback_range = min(5, current_step.step_number)
        lookback_start = max(0, current_step.step_number - lookback_range)
        
        for i in range(lookback_start, current_step.step_number):
            if i < len(trajectory.steps):
                prev_step = trajectory.steps[i]
                
                # Check if action type matches
                if prev_step.action_type == current_step.action_type:
                    # Check if target is similar (within 50 pixels)
                    if current_step.action_coords and prev_step.action_coords:
                        dx = abs(current_step.action_coords[0] - prev_step.action_coords[0])
                        dy = abs(current_step.action_coords[1] - prev_step.action_coords[1])
                        
                        if dx < 50 and dy < 50:
                            similar.append(prev_step)
        
        return similar
    
    def _determine_recovery_success(self) -> bool:
        """
        Determine if recovery succeeds.
        
        LOOP recovery has higher success rate because backtracking is reliable.
        
        Returns:
            True if recovery succeeds
        """
        success_rate = self.config.recovery_success_rates.get("LOOP", 0.75)
        return random.random() < success_rate
