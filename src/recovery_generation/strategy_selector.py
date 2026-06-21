"""
Strategy Selector

Maps failure types to appropriate recovery strategies using rule-based mapping.
Provides primary and fallback strategies for each failure type.

Strategy Selection Logic:
- Each failure type has a primary strategy
- Secondary (fallback) strategy if primary fails
- Can override with custom mappings
- Considers failure severity and recoverability
"""

from typing import List, Optional, Tuple, Union, Dict, Any
from dataclasses import dataclass

try:
    from ..failure_labeling.failure_schema import FailureType, FailureLabel
except ImportError:
    from failure_labeling.failure_schema import FailureType, FailureLabel

try:
    from .recovery_schema import RecoveryStrategy
except ImportError:
    from recovery_generation.recovery_schema import RecoveryStrategy


@dataclass
class StrategyMapping:
    """Mapping of failure type to recovery strategies.
    
    Defines primary and secondary strategies for a failure type.
    """
    
    failure_type: FailureType
    primary_strategy: RecoveryStrategy
    secondary_strategy: RecoveryStrategy
    priority: int = 50  # Higher = more preferred


class StrategySelector:
    """Selects appropriate recovery strategies for detected failures.
    
    Uses rule-based mapping with primary/secondary strategy selection.
    Considers failure type, severity, and recoverability.
    
    Usage:
        selector = StrategySelector()
        strategy = selector.select_strategy(failure_label)
    """
    
    def __init__(self):
        """Initialize strategy selector with default mappings."""
        self.mappings = self._create_default_mappings()
    
    def _create_default_mappings(self) -> List[StrategyMapping]:
        """Create default failure-to-strategy mappings.
        
        Based on failure type characteristics and likelihood of success.
        
        Returns:
            List of strategy mappings
        """
        mappings = []
        
        # PERCEPTION_ERROR: Element not found -> try alternatives
        mappings.append(StrategyMapping(
            failure_type=FailureType.PERCEPTION_ERROR,
            primary_strategy=RecoveryStrategy.ALTERNATIVE_TARGET,
            secondary_strategy=RecoveryStrategy.REPLAN,
            priority=90,
        ))
        
        # ACTION_MISMATCH: Wrong action -> retry or try alternatives
        mappings.append(StrategyMapping(
            failure_type=FailureType.ACTION_MISMATCH,
            primary_strategy=RecoveryStrategy.RETRY,
            secondary_strategy=RecoveryStrategy.ALTERNATIVE_TARGET,
            priority=85,
        ))
        
        # STATE_NO_CHANGE: No effect -> retry or backtrack
        mappings.append(StrategyMapping(
            failure_type=FailureType.STATE_NO_CHANGE,
            primary_strategy=RecoveryStrategy.RETRY,
            secondary_strategy=RecoveryStrategy.BACKTRACK,
            priority=80,
        ))
        
        # LOOP_DETECTED: Stuck in loop -> backtrack or replan
        mappings.append(StrategyMapping(
            failure_type=FailureType.LOOP_DETECTED,
            primary_strategy=RecoveryStrategy.BACKTRACK,
            secondary_strategy=RecoveryStrategy.REPLAN,
            priority=95,  # High priority - loops are serious
        ))
        
        # GOAL_MISALIGNMENT: Wrong path -> replan or abort
        mappings.append(StrategyMapping(
            failure_type=FailureType.GOAL_MISALIGNMENT,
            primary_strategy=RecoveryStrategy.REPLAN,
            secondary_strategy=RecoveryStrategy.ABORT,
            priority=75,
        ))
        
        # TOOL_FAILURE: Browser error -> retry or abort
        mappings.append(StrategyMapping(
            failure_type=FailureType.TOOL_FAILURE,
            primary_strategy=RecoveryStrategy.RETRY,
            secondary_strategy=RecoveryStrategy.ABORT,
            priority=70,
        ))
        
        # UI_VARIATION: Unexpected UI change -> try alternatives or replan
        mappings.append(StrategyMapping(
            failure_type=FailureType.UI_VARIATION,
            primary_strategy=RecoveryStrategy.ALTERNATIVE_TARGET,
            secondary_strategy=RecoveryStrategy.REPLAN,
            priority=65,
        ))
        
        # REASONING_ERROR: Logical error -> replan or backtrack
        mappings.append(StrategyMapping(
            failure_type=FailureType.REASONING_ERROR,
            primary_strategy=RecoveryStrategy.REPLAN,
            secondary_strategy=RecoveryStrategy.BACKTRACK,
            priority=60,
        ))
        
        # NONE: No failure -> no recovery needed (shouldn't reach here)
        mappings.append(StrategyMapping(
            failure_type=FailureType.NONE,
            primary_strategy=RecoveryStrategy.ABORT,
            secondary_strategy=RecoveryStrategy.ABORT,
            priority=0,
        ))
        
        return mappings
    
    def select_strategy(
        self,
        failure_label: Union[FailureLabel, Dict[str, Any], str],
        attempt_number: int = 1,
        severity: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> RecoveryStrategy:
        """Select recovery strategy for a failure.
        
        Args:
            failure_label: The detected failure (FailureLabel, dict, or failure_type string)
            attempt_number: Current attempt number (1 for first, 2+ for retries)
            severity: Optional severity override
            confidence: Optional confidence override
            
        Returns:
            Selected recovery strategy
        """
        # Handle different input types
        if isinstance(failure_label, str):
            failure_type_str = failure_label
            # Convert to lowercase with underscores (enum format)
            failure_type_enum_str = failure_type_str.lower()
            try:
                failure_type = FailureType(failure_type_enum_str)
            except (ValueError, KeyError):
                failure_type = None
            severity = severity or 0.5
            confidence = confidence or 0.5
        elif isinstance(failure_label, dict):
            failure_type_str = failure_label.get("failure_type", "UNKNOWN")
            # Convert to lowercase with underscores (enum format)
            failure_type_enum_str = failure_type_str.lower()
            try:
                failure_type = FailureType(failure_type_enum_str)
            except (ValueError, KeyError):
                failure_type = None
            severity = severity or failure_label.get("severity", 0.5)
            confidence = confidence or failure_label.get("confidence", 0.5)
        else:
            # FailureLabel object
            failure_type = failure_label.failure_type
            failure_type_str = failure_type.value if hasattr(failure_type, 'value') else str(failure_type)
            severity = severity or failure_label.failure_severity
            confidence = confidence or failure_label.confidence
        
        # No recovery needed for successful steps
        if failure_type == FailureType.NONE:
            return RecoveryStrategy.ABORT
        
        # Find mapping for this failure type
        mapping = self._get_mapping(failure_type)
        
        if mapping is None:
            # Default fallback: RETRY for first attempt, ABORT for subsequent
            return RecoveryStrategy.RETRY if attempt_number == 1 else RecoveryStrategy.ABORT
        
        # Create a simple object for _adjust_strategy
        class SimpleFailure:
            def __init__(self, ftype, sev, conf):
                self.failure_type = ftype
                self.confidence = conf
                self.recoverable = True  # Default to recoverable
                # Convert numeric severity to string
                if sev >= 0.7:
                    self.severity = "high"
                elif sev >= 0.4:
                    self.severity = "medium"
                else:
                    self.severity = "low"
        
        simple_failure = SimpleFailure(failure_type, severity, confidence)
        
        # Use primary strategy for first attempt
        if attempt_number == 1:
            return self._adjust_strategy(mapping.primary_strategy, simple_failure)
        
        # Use secondary strategy for subsequent attempts
        else:
            return self._adjust_strategy(mapping.secondary_strategy, simple_failure)
    
    def get_strategy_sequence(
        self,
        failure_label: Union[FailureLabel, Dict[str, Any], str],
        max_attempts: int = 3,
        severity: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> List[RecoveryStrategy]:
        """Get sequence of strategies to try for a failure.
        
        Args:
            failure_label: The detected failure
            max_attempts: Maximum number of attempts
            severity: Optional severity override
            confidence: Optional confidence override
            
        Returns:
            List of strategies in order of preference
        """
        strategies = []
        
        for attempt in range(1, max_attempts + 1):
            strategy = self.select_strategy(failure_label, attempt, severity, confidence)
            
            # Don't repeat ABORT
            if strategy == RecoveryStrategy.ABORT and RecoveryStrategy.ABORT in strategies:
                break
            
            strategies.append(strategy)
            
            # Stop after ABORT
            if strategy == RecoveryStrategy.ABORT:
                break
        
        return strategies
    
    def _get_mapping(self, failure_type: FailureType) -> Optional[StrategyMapping]:
        """Get strategy mapping for failure type.
        
        Args:
            failure_type: Type of failure
            
        Returns:
            Strategy mapping or None if not found
        """
        for mapping in self.mappings:
            if mapping.failure_type == failure_type:
                return mapping
        return None
    
    def _adjust_strategy(
        self,
        strategy: RecoveryStrategy,
        failure_label: FailureLabel,
    ) -> RecoveryStrategy:
        """Adjust strategy based on failure characteristics.
        
        May override strategy based on severity, recoverability, etc.
        
        Args:
            strategy: Initially selected strategy
            failure_label: Failure details
            
        Returns:
            Potentially adjusted strategy
        """
        # High severity + not recoverable -> prefer ABORT
        if (failure_label.severity == "high" and 
            failure_label.recoverable is False):
            if strategy not in [RecoveryStrategy.ABORT, RecoveryStrategy.REPLAN]:
                # Still try REPLAN once before aborting
                return RecoveryStrategy.REPLAN if failure_label.confidence > 0.7 else RecoveryStrategy.ABORT
        
        # Low confidence in failure diagnosis -> prefer RETRY (might be false positive)
        if failure_label.confidence < 0.5:
            if strategy == RecoveryStrategy.ABORT:
                return RecoveryStrategy.RETRY
        
        # Tool failures with high confidence -> abort faster
        if (failure_label.failure_type == FailureType.TOOL_FAILURE and 
            failure_label.confidence > 0.8):
            if strategy == RecoveryStrategy.RETRY:
                # Allow one retry then abort
                return strategy
        
        return strategy
    
    def add_custom_mapping(
        self,
        failure_type: Union[FailureType, str],
        primary: Optional[RecoveryStrategy] = None,
        secondary: Optional[RecoveryStrategy] = None,
        primary_strategy: Optional[RecoveryStrategy] = None,
        secondary_strategy: Optional[RecoveryStrategy] = None,
        priority: int = 50,
    ) -> None:
        """Add or override a strategy mapping.
        
        Args:
            failure_type: Type of failure (FailureType or string)
            primary: Primary recovery strategy (alias for primary_strategy)
            secondary: Secondary fallback strategy (alias for secondary_strategy)
            primary_strategy: Primary recovery strategy
            secondary_strategy: Secondary fallback strategy
            priority: Priority level (higher = more preferred)
        """
        # Handle string failure_type
        if isinstance(failure_type, str):
            # Try to convert to FailureType (convert to lowercase format)
            failure_type_lower = failure_type.lower()
            try:
                failure_type = FailureType(failure_type_lower)
            except (ValueError, KeyError):
                # Create a custom string-based failure type (not ideal but allows flexibility)
                # For now, just skip if invalid
                return
        
        # Handle parameter aliases
        primary_strat = primary or primary_strategy
        secondary_strat = secondary or secondary_strategy or RecoveryStrategy.ABORT
        
        if primary_strat is None:
            raise ValueError("Must provide primary or primary_strategy")
        
        # Remove existing mapping if present
        self.mappings = [m for m in self.mappings if m.failure_type != failure_type]
        
        # Add new mapping
        self.mappings.append(StrategyMapping(
            failure_type=failure_type,
            primary_strategy=primary_strat,
            secondary_strategy=secondary_strat,
            priority=priority,
        ))
    
    def get_strategy_stats(self) -> dict:
        """Get statistics about strategy mappings.
        
        Returns:
            Dictionary with mapping statistics
        """
        strategy_counts = {}
        for mapping in self.mappings:
            primary = mapping.primary_strategy.value
            secondary = mapping.secondary_strategy.value
            
            strategy_counts[primary] = strategy_counts.get(primary, 0) + 1
            strategy_counts[secondary] = strategy_counts.get(secondary, 0) + 1
        
        return {
            "total_mappings": len(self.mappings),
            "strategy_distribution": strategy_counts,
            "failure_types_covered": [m.failure_type.value for m in self.mappings],
        }
