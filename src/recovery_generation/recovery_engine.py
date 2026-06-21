"""
Recovery Engine

Main orchestration class for recovery generation system.
Coordinates:
- Failure detection (from failure_labeling)
- Strategy selection
- Recovery execution
- Success evaluation (using metrics)
- Multi-step recovery workflows

Uses pipeline from previous tasks:
- Task-04 (Failure Labeling): Detect and classify failures
- Task-03 (Metric Computation): Evaluate recovery success
- Task-02 (Browser Recorder): Execute recovery actions
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

try:
    from .recovery_schema import (
        RecoveryStrategy,
        RecoveryOutcome,
        RecoveryResult,
        RecoveryAttempt,
        RecoveryConfig,
        DEFAULT_RECOVERY_CONFIG,
        create_recovery_result,
        create_abort_result,
    )
    from .strategy_selector import StrategySelector
    from .recovery_executor import (
        RecoveryExecutor,
        RetryExecutor,
        BacktrackExecutor,
        AlternativeTargetExecutor,
        ReplanExecutor,
        AbortExecutor,
    )
except ImportError:
    from recovery_generation.recovery_schema import (
        RecoveryStrategy,
        RecoveryOutcome,
        RecoveryResult,
        RecoveryAttempt,
        RecoveryConfig,
        DEFAULT_RECOVERY_CONFIG,
        create_recovery_result,
        create_abort_result,
    )
    from recovery_generation.strategy_selector import StrategySelector
    from recovery_generation.recovery_executor import (
        RecoveryExecutor,
        RetryExecutor,
        BacktrackExecutor,
        AlternativeTargetExecutor,
        ReplanExecutor,
        AbortExecutor,
    )


@dataclass
class RecoveryStats:
    """Statistics for recovery operations.
    
    Tracks success rates, timing, and strategy effectiveness.
    """
    
    total_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    aborted_recoveries: int = 0
    
    # Per-strategy stats
    strategy_attempts: Dict[RecoveryStrategy, int] = field(default_factory=dict)
    strategy_successes: Dict[RecoveryStrategy, int] = field(default_factory=dict)
    
    # Timing
    total_recovery_time_ms: float = 0.0
    avg_recovery_time_ms: float = 0.0
    
    def update(self, attempt: RecoveryAttempt) -> None:
        """Update stats with new recovery attempt.
        
        Args:
            attempt: Completed recovery attempt
        """
        self.total_attempts += 1
        
        if attempt.success:
            self.successful_recoveries += 1
        elif attempt.final_result.outcome == RecoveryOutcome.ABORTED:
            self.aborted_recoveries += 1
        else:
            self.failed_recoveries += 1
        
        # Update strategy stats
        for result in attempt.recovery_results:
            strategy = result.strategy
            self.strategy_attempts[strategy] = self.strategy_attempts.get(strategy, 0) + 1
            if result.success:
                self.strategy_successes[strategy] = self.strategy_successes.get(strategy, 0) + 1
        
        # Update timing
        self.total_recovery_time_ms += attempt.total_duration_ms
        if self.total_attempts > 0:
            self.avg_recovery_time_ms = self.total_recovery_time_ms / self.total_attempts
    
    def get_success_rate(self) -> float:
        """Get overall recovery success rate.
        
        Returns:
            Success rate (0.0 to 1.0)
        """
        if self.total_attempts == 0:
            return 0.0
        return self.successful_recoveries / self.total_attempts
    
    def get_strategy_success_rate(self, strategy: RecoveryStrategy) -> float:
        """Get success rate for specific strategy.
        
        Args:
            strategy: Recovery strategy
            
        Returns:
            Success rate for this strategy (0.0 to 1.0)
        """
        attempts = self.strategy_attempts.get(strategy, 0)
        if attempts == 0:
            return 0.0
        successes = self.strategy_successes.get(strategy, 0)
        return successes / attempts


class RecoveryEngine:
    """Main recovery generation system.
    
    Orchestrates complete recovery workflows:
    1. Receive failure detection from Task-04
    2. Select appropriate recovery strategy
    3. Execute recovery actions
    4. Evaluate success using Task-03 metrics
    5. Try alternative strategies if needed
    6. Record complete recovery attempt
    """
    
    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        strategy_selector: Optional[StrategySelector] = None,
    ):
        """Initialize recovery engine.
        
        Args:
            config: Recovery configuration
            strategy_selector: Strategy selector (creates default if not provided)
        """
        self.config = config or DEFAULT_RECOVERY_CONFIG
        self.selector = strategy_selector or StrategySelector()
        self.stats = RecoveryStats()
        
        # Initialize executors for each strategy
        self.executors: Dict[RecoveryStrategy, RecoveryExecutor] = {
            RecoveryStrategy.RETRY: RetryExecutor(self.config),
            RecoveryStrategy.BACKTRACK: BacktrackExecutor(self.config),
            RecoveryStrategy.ALTERNATIVE_TARGET: AlternativeTargetExecutor(self.config),
            RecoveryStrategy.REPLAN: ReplanExecutor(self.config),
            RecoveryStrategy.ABORT: AbortExecutor(self.config),
        }
    
    def recover_from_failure(
        self,
        failure_label: Dict[str, Any],
        context: Dict[str, Any],
        max_attempts: Optional[int] = None,
    ) -> RecoveryAttempt:
        """Attempt to recover from a detected failure.
        
        Main entry point for recovery system. Tries multiple strategies
        until recovery succeeds or all options are exhausted.
        
        Args:
            failure_label: Failure detection from Task-04 (FailureLabel dict)
            context: Recovery context:
                - failed_action: The action that failed
                - current_state: Current page state
                - state_history: Previous states (for backtracking)
                - goal: Task goal description
                - alternative_selectors: Alternative element selectors
            max_attempts: Override max attempts from config
            
        Returns:
            RecoveryAttempt with all results and final outcome
        """
        start_time = time.time()
        max_attempts = max_attempts or self.config.max_total_attempts
        
        # Extract failure info
        failure_type = failure_label.get("failure_type")
        severity = failure_label.get("severity", 0.5)
        confidence = failure_label.get("confidence", 0.5)
        
        if not failure_type:
            # No failure type - abort immediately
            abort_result = create_abort_result("No failure type provided")
            return RecoveryAttempt(
                failure_type="unknown",  # Provide string default
                failure_severity=severity,
                recovery_results=[abort_result],
                final_result=abort_result,
                success=False,
                total_duration_ms=abort_result.duration_ms,
            )
        
        # Get strategy sequence to try
        strategy_sequence = self.selector.get_strategy_sequence(
            failure_label=failure_type,
            severity=severity,
            confidence=confidence,
        )
        
        recovery_results: List[RecoveryResult] = []
        attempt_number = 0
        
        # Try each strategy in sequence
        for strategy in strategy_sequence:
            if attempt_number >= max_attempts:
                break
            
            attempt_number += 1
            
            # Execute recovery with this strategy
            result = self._execute_recovery(
                strategy=strategy,
                context=context,
                attempt_number=attempt_number,
            )
            
            recovery_results.append(result)
            
            # Check if recovery succeeded
            if result.success:
                # Success! Create successful attempt record
                total_duration_ms = (time.time() - start_time) * 1000
                attempt = RecoveryAttempt(
                    failure_type=failure_type,
                    failure_severity=severity,
                    recovery_results=recovery_results,
                    final_result=result,
                    success=True,
                    total_duration_ms=total_duration_ms,
                )
                self.stats.update(attempt)
                return attempt
            
            # Check if we should abort
            if result.outcome == RecoveryOutcome.ABORTED:
                break
        
        # All strategies failed - create failed attempt record
        total_duration_ms = (time.time() - start_time) * 1000
        final_result = recovery_results[-1] if recovery_results else create_abort_result(
            "No recovery strategies attempted"
        )
        
        attempt = RecoveryAttempt(
            failure_type=failure_type,
            failure_severity=severity,
            recovery_results=recovery_results,
            final_result=final_result,
            success=False,
            total_duration_ms=total_duration_ms,
        )
        
        self.stats.update(attempt)
        return attempt
    
    def _execute_recovery(
        self,
        strategy: RecoveryStrategy,
        context: Dict[str, Any],
        attempt_number: int,
    ) -> RecoveryResult:
        """Execute single recovery strategy.
        
        Args:
            strategy: Strategy to execute
            context: Recovery context
            attempt_number: Attempt number
            
        Returns:
            RecoveryResult with outcome
        """
        executor = self.executors.get(strategy)
        if not executor:
            return create_abort_result(
                f"No executor for strategy: {strategy}",
                duration_ms=0.0,
            )
        
        try:
            result = executor.execute(context, attempt_number)
            
            # Evaluate success using context (in production, use Task-03 metrics)
            # For now, result success is determined by executor
            # In full system, this would:
            # 1. Execute actions using Task-02 Browser Recorder
            # 2. Capture new metrics using Task-03 Metric Computation
            # 3. Compare metrics to determine if recovery succeeded
            
            return result
            
        except Exception as e:
            # Execution failed - return failure result
            return RecoveryResult(
                strategy=strategy,
                outcome=RecoveryOutcome.FAILURE,
                actions_taken=[],
                success=False,
                duration_ms=0.0,
                confidence=0.0,
                error_message=str(e),
            )
    
    def get_stats(self) -> RecoveryStats:
        """Get recovery statistics.
        
        Returns:
            RecoveryStats with success rates and timing
        """
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = RecoveryStats()
    
    def add_custom_strategy_mapping(
        self,
        failure_type: str,
        primary: RecoveryStrategy,
        secondary: Optional[RecoveryStrategy] = None,
        priority: int = 1,
    ) -> None:
        """Add custom strategy mapping.
        
        Allows overriding default failure-to-strategy mappings.
        
        Args:
            failure_type: Failure type from Task-04
            primary: Primary recovery strategy
            secondary: Secondary (fallback) strategy
            priority: Priority level (higher = more important)
        """
        self.selector.add_custom_mapping(
            failure_type=failure_type,
            primary=primary,
            secondary=secondary,
            priority=priority,
        )
    
    def evaluate_recovery_success(
        self,
        pre_recovery_metrics: Dict[str, Any],
        post_recovery_metrics: Dict[str, Any],
        goal_criteria: Dict[str, Any],
    ) -> bool:
        """Evaluate if recovery was successful.
        
        Compares metrics before and after recovery attempt to determine
        if the recovery successfully resolved the failure.
        
        Args:
            pre_recovery_metrics: Metrics from Task-03 before recovery
            post_recovery_metrics: Metrics from Task-03 after recovery
            goal_criteria: Success criteria for the task
            
        Returns:
            True if recovery succeeded, False otherwise
        """
        # Check if state changed meaningfully
        if self._metrics_improved(pre_recovery_metrics, post_recovery_metrics):
            return True
        
        # Check if goal criteria met
        if self._goal_criteria_met(post_recovery_metrics, goal_criteria):
            return True
        
        return False
    
    def _metrics_improved(
        self,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
    ) -> bool:
        """Check if metrics improved after recovery.
        
        Args:
            pre_metrics: Metrics before recovery
            post_metrics: Metrics after recovery
            
        Returns:
            True if metrics improved
        """
        # Visual similarity should increase (less MSE)
        pre_mse = pre_metrics.get("visual", {}).get("mse", float("inf"))
        post_mse = post_metrics.get("visual", {}).get("mse", float("inf"))
        
        if post_mse < pre_mse * 0.9:  # 10% improvement threshold
            return True
        
        # Content hash should differ (state changed)
        pre_hash = pre_metrics.get("content_hash")
        post_hash = post_metrics.get("content_hash")
        
        if pre_hash and post_hash and pre_hash != post_hash:
            return True
        
        return False
    
    def _goal_criteria_met(
        self,
        metrics: Dict[str, Any],
        criteria: Dict[str, Any],
    ) -> bool:
        """Check if goal criteria are met.
        
        Args:
            metrics: Current metrics
            criteria: Goal criteria to check
            
        Returns:
            True if criteria met
        """
        # Example criteria checks
        # In production, this would be more sophisticated
        
        # URL criteria
        target_url = criteria.get("target_url")
        current_url = metrics.get("metadata", {}).get("url")
        if target_url and current_url:
            if target_url in current_url:
                return True
        
        # Element visibility criteria
        target_element = criteria.get("target_element")
        visible_elements = metrics.get("action", {}).get("clickable_elements", [])
        if target_element and target_element in visible_elements:
            return True
        
        return False
