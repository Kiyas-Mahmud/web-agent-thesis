"""
Recovery Executor

Implements execution logic for all 5 recovery strategies:
1. RETRY - Re-execute the same action with backoff
2. BACKTRACK - Revert to previous state and try different path
3. ALTERNATIVE_TARGET - Try different element with similar semantics
4. REPLAN - Generate new action sequence from current state
5. ABORT - Terminate gracefully

Each executor returns a RecoveryResult with outcome and actions taken.
"""

import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

try:
    from .recovery_schema import (
        RecoveryStrategy,
        RecoveryOutcome,
        RecoveryAction,
        RecoveryResult,
        RecoveryConfig,
        DEFAULT_RECOVERY_CONFIG,
        create_recovery_result,
        create_abort_result,
    )
except ImportError:
    from recovery_generation.recovery_schema import (
        RecoveryStrategy,
        RecoveryOutcome,
        RecoveryAction,
        RecoveryResult,
        RecoveryConfig,
        DEFAULT_RECOVERY_CONFIG,
        create_recovery_result,
        create_abort_result,
    )


class RecoveryExecutor(ABC):
    """Base class for recovery strategy executors.
    
    Each strategy has its own executor subclass that implements
    the specific recovery logic.
    """
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        """Initialize executor.
        
        Args:
            config: Recovery configuration (uses default if not provided)
        """
        self.config = config or DEFAULT_RECOVERY_CONFIG
    
    @abstractmethod
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute recovery strategy.
        
        Args:
            context: Recovery context (failed action, state, etc.)
            attempt_number: Current attempt number
            
        Returns:
            RecoveryResult with outcome
        """
        pass
    
    def _create_action(
        self,
        action_type: str,
        action_args: Dict[str, Any],
        expected_outcome: Optional[str] = None,
    ) -> RecoveryAction:
        """Helper to create a RecoveryAction.
        
        Args:
            action_type: Type of action
            action_args: Action arguments
            expected_outcome: Expected outcome
            
        Returns:
            RecoveryAction instance
        """
        return RecoveryAction(
            action_type=action_type,
            action_args=action_args,
            expected_outcome=expected_outcome,
            timeout_ms=self.config.recovery_timeout_ms,
        )


class RetryExecutor(RecoveryExecutor):
    """Executes RETRY strategy.
    
    Re-executes the same action that failed, optionally with backoff delay.
    Most useful for transient failures (timeouts, temporary unavailability).
    """
    
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute retry recovery.
        
        Args:
            context: Must contain 'failed_action' key with action details
            attempt_number: Current attempt number
            
        Returns:
            RecoveryResult with actions to retry
        """
        start_time = time.time()
        
        # Check if max attempts exceeded
        if attempt_number > self.config.retry_max_attempts:
            return create_abort_result(
                f"Max retry attempts ({self.config.retry_max_attempts}) exceeded",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Get failed action from context
        failed_action = context.get("failed_action")
        if not failed_action:
            return create_abort_result(
                "No failed action in context",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Create retry action (same as original)
        retry_action = self._create_action(
            action_type=failed_action.get("type", "unknown"),
            action_args=failed_action.get("args", {}),
            expected_outcome="Action succeeds this time",
        )
        
        # Calculate backoff delay for subsequent attempts
        backoff_ms = 0
        if attempt_number > 1:
            # Exponential backoff: base_delay * 2^(attempt-2)
            backoff_ms = self.config.retry_backoff_ms * (2 ** (attempt_number - 2))
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Return result with retry action
        # Note: Actual execution happens in RecoveryEngine
        return RecoveryResult(
            strategy=RecoveryStrategy.RETRY,
            outcome=RecoveryOutcome.PARTIAL,  # Execution not done yet
            actions_taken=[retry_action],
            success=False,  # Will be determined after execution
            duration_ms=duration_ms,
            confidence=max(0.7 - (attempt_number - 1) * 0.2, 0.2),  # Lower confidence for more retries
        )


class BacktrackExecutor(RecoveryExecutor):
    """Executes BACKTRACK strategy.
    
    Reverts to a previous state and tries a different action sequence.
    Useful when the current path led to a dead end or loop.
    """
    
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute backtrack recovery.
        
        Args:
            context: Must contain 'state_history' with previous states
            attempt_number: Current attempt number
            
        Returns:
            RecoveryResult with backtrack actions
        """
        start_time = time.time()
        
        # Get state history
        state_history = context.get("state_history", [])
        if not state_history:
            return create_abort_result(
                "No state history available for backtracking",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Determine how many steps to backtrack
        # Backtrack more steps on subsequent attempts
        backtrack_steps = min(attempt_number, self.config.backtrack_max_steps)
        backtrack_steps = min(backtrack_steps, len(state_history))
        
        if backtrack_steps == 0:
            return create_abort_result(
                "Cannot backtrack (at initial state)",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Create navigation action to previous state
        target_state = state_history[-(backtrack_steps)]
        
        backtrack_action = self._create_action(
            action_type="navigate",
            action_args={"url": target_state.get("url", ""), "wait_for_load": True},
            expected_outcome=f"Return to state from {backtrack_steps} steps ago",
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        return RecoveryResult(
            strategy=RecoveryStrategy.BACKTRACK,
            outcome=RecoveryOutcome.PARTIAL,
            actions_taken=[backtrack_action],
            success=False,
            duration_ms=duration_ms,
            confidence=0.6,  # Moderate confidence
        )


class AlternativeTargetExecutor(RecoveryExecutor):
    """Executes ALTERNATIVE_TARGET strategy.
    
    Tries to find and interact with an alternative element when the
    original target cannot be found or interacted with.
    """
    
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute alternative target recovery.
        
        Args:
            context: Must contain 'failed_action' and optionally 'alternative_selectors'
            attempt_number: Current attempt number
            
        Returns:
            RecoveryResult with alternative target actions
        """
        start_time = time.time()
        
        failed_action = context.get("failed_action")
        if not failed_action:
            return create_abort_result(
                "No failed action in context",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Get alternative selectors
        alternatives = context.get("alternative_selectors", [])
        
        # If no alternatives provided, generate common variations
        if not alternatives:
            original_selector = failed_action.get("args", {}).get("selector", "")
            alternatives = self._generate_alternative_selectors(original_selector)
        
        # Limit to max candidates
        alternatives = alternatives[:self.config.alternative_max_candidates]
        
        if not alternatives:
            return create_abort_result(
                "No alternative selectors available",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Select alternative based on attempt number
        if attempt_number > len(alternatives):
            return create_abort_result(
                f"Exhausted all {len(alternatives)} alternatives",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        alternative_selector = alternatives[attempt_number - 1]
        
        # Create action with alternative selector
        action_type = failed_action.get("type", "click")
        action_args = failed_action.get("args", {}).copy()
        action_args["selector"] = alternative_selector
        
        alternative_action = self._create_action(
            action_type=action_type,
            action_args=action_args,
            expected_outcome=f"Interact with alternative element: {alternative_selector}",
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        return RecoveryResult(
            strategy=RecoveryStrategy.ALTERNATIVE_TARGET,
            outcome=RecoveryOutcome.PARTIAL,
            actions_taken=[alternative_action],
            success=False,
            duration_ms=duration_ms,
            confidence=0.5 - (attempt_number - 1) * 0.1,  # Lower confidence for later alternatives
        )
    
    def _generate_alternative_selectors(self, original: str) -> List[str]:
        """Generate alternative selectors from original.
        
        Creates variations by modifying CSS selector strategies.
        
        Args:
            original: Original selector that failed
            
        Returns:
            List of alternative selectors to try
        """
        alternatives = []
        
        if not original:
            return alternatives
        
        # If it's an ID selector, try class-based
        if original.startswith("#"):
            base = original[1:]
            alternatives.append(f".{base}")
            alternatives.append(f"[id='{base}']")
            alternatives.append(f"[id*='{base}']")  # Contains
        
        # If it's a class selector, try variations
        elif original.startswith("."):
            base = original[1:]
            alternatives.append(f"#{base}")
            alternatives.append(f"[class='{base}']")
            alternatives.append(f"[class*='{base}']")
        
        # For other selectors, try more generic versions
        else:
            # Remove :nth-child if present
            if ":nth-child" in original:
                alternatives.append(original.split(":nth-child")[0])
            
            # Try just the tag name
            if " " in original:
                alternatives.append(original.split()[-1])
            
            # Try with wildcard
            alternatives.append(f"{original}, {original} *")
        
        return alternatives


class ReplanExecutor(RecoveryExecutor):
    """Executes REPLAN strategy.
    
    Generates a new action sequence from the current state.
    Most complex strategy - uses heuristics to determine next best actions.
    """
    
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute replan recovery.
        
        Args:
            context: Must contain 'goal' and 'current_state'
            attempt_number: Current attempt number
            
        Returns:
            RecoveryResult with replanned actions
        """
        start_time = time.time()
        
        if attempt_number > self.config.replan_max_attempts:
            return create_abort_result(
                f"Max replan attempts ({self.config.replan_max_attempts}) exceeded",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        goal = context.get("goal")
        current_state = context.get("current_state", {})
        failed_action = context.get("failed_action", {})
        
        if not goal:
            return create_abort_result(
                "No goal specified for replanning",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Generate alternative action sequence
        # This is a simple heuristic-based approach
        # In production, this would use an LLM or planning algorithm
        replanned_actions = self._generate_alternative_plan(
            goal=goal,
            current_state=current_state,
            failed_action=failed_action,
            attempt_number=attempt_number,
        )
        
        if not replanned_actions:
            return create_abort_result(
                "Could not generate alternative plan",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        duration_ms = (time.time() - start_time) * 1000
        
        return RecoveryResult(
            strategy=RecoveryStrategy.REPLAN,
            outcome=RecoveryOutcome.PARTIAL,
            actions_taken=replanned_actions,
            success=False,
            duration_ms=duration_ms,
            confidence=0.4,  # Lower confidence for heuristic planning
        )
    
    def _generate_alternative_plan(
        self,
        goal: str,
        current_state: Dict[str, Any],
        failed_action: Dict[str, Any],
        attempt_number: int,
    ) -> List[RecoveryAction]:
        """Generate alternative action sequence.
        
        Simple heuristic-based planning. In production, this would use
        an LLM or more sophisticated planning algorithm.
        
        Args:
            goal: Goal description
            current_state: Current page state
            failed_action: Action that failed
            attempt_number: Attempt number
            
        Returns:
            List of alternative actions
        """
        actions = []
        
        # Heuristic 1: If a click failed, try scrolling first
        if failed_action.get("type") == "click":
            actions.append(self._create_action(
                action_type="scroll",
                action_args={"direction": "down", "amount": 300},
                expected_outcome="Scroll to reveal target element",
            ))
            
            # Then retry the click
            actions.append(self._create_action(
                action_type="click",
                action_args=failed_action.get("args", {}),
                expected_outcome="Click after scrolling",
            ))
        
        # Heuristic 2: If typing failed, try clicking first to focus
        elif failed_action.get("type") == "type":
            selector = failed_action.get("args", {}).get("selector", "")
            actions.append(self._create_action(
                action_type="click",
                action_args={"selector": selector},
                expected_outcome="Focus input field",
            ))
            
            actions.append(self._create_action(
                action_type="type",
                action_args=failed_action.get("args", {}),
                expected_outcome="Type after focusing",
            ))
        
        # Heuristic 3: If navigate failed, try reload
        elif failed_action.get("type") == "navigate":
            actions.append(self._create_action(
                action_type="navigate",
                action_args={"url": current_state.get("url", ""), "refresh": True},
                expected_outcome="Reload current page",
            ))
        
        # Heuristic 4: Default - wait and retry
        else:
            actions.append(self._create_action(
                action_type="wait",
                action_args={"duration_ms": 2000},
                expected_outcome="Wait for page to stabilize",
            ))
            
            actions.append(self._create_action(
                action_type=failed_action.get("type", "click"),
                action_args=failed_action.get("args", {}),
                expected_outcome="Retry after waiting",
            ))
        
        return actions


class AbortExecutor(RecoveryExecutor):
    """Executes ABORT strategy.
    
    Terminates recovery attempt gracefully when failure is unrecoverable
    or recovery attempts have been exhausted.
    """
    
    def execute(
        self,
        context: Dict[str, Any],
        attempt_number: int = 1,
    ) -> RecoveryResult:
        """Execute abort.
        
        Args:
            context: Recovery context
            attempt_number: Attempt number
            
        Returns:
            RecoveryResult indicating abort
        """
        reason = context.get("abort_reason", "Recovery deemed impossible or unwise")
        
        return create_abort_result(
            reason=reason,
            duration_ms=0.0,
        )
