"""
Memory Signal Detector

Detects when agent experiences should be flagged for memory updates.
Memory-worthy events include:
- Novel failure patterns (new failure types)
- Successful recovery from failures
- High uncertainty situations
- Surprising outcomes
"""

from typing import Dict, Any, Optional, List, Set

try:
    from .reflection_schema import MemoryType, ReflectionConfig, DEFAULT_REFLECTION_CONFIG
except ImportError:
    from reflection_annotation.reflection_schema import MemoryType, ReflectionConfig, DEFAULT_REFLECTION_CONFIG


class MemorySignalDetector:
    """Detects memory-worthy experiences.
    
    Maintains history of seen patterns to detect novelty.
    """
    
    def __init__(self, config: Optional[ReflectionConfig] = None):
        """Initialize memory signal detector.
        
        Args:
            config: Reflection configuration
        """
        self.config = config or DEFAULT_REFLECTION_CONFIG
        
        # Track seen patterns for novelty detection
        self.seen_failure_types: Set[str] = set()
        self.seen_recovery_strategies: Set[str] = set()
        self.seen_action_patterns: Set[str] = set()
        
        # Statistics
        self.total_steps = 0
        self.memory_signals = 0
    
    def detect_memory_signal(
        self,
        confidence_before: float,
        confidence_after: float,
        failure_info: Optional[Dict[str, Any]] = None,
        recovery_info: Optional[Dict[str, Any]] = None,
        outcome: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, MemoryType]:
        """Detect if experience should be flagged for memory update.
        
        Args:
            confidence_before: Confidence before action
            confidence_after: Confidence after action
            failure_info: Failure detection info
            recovery_info: Recovery attempt info
            outcome: Action outcome info
            
        Returns:
            Tuple of (memory_update_flag, memory_type)
        """
        self.total_steps += 1
        
        # Check various criteria
        memory_type = MemoryType.NONE
        should_update = False
        
        # 1. Novel failure pattern
        if self._is_novel_failure(failure_info):
            memory_type = MemoryType.FAILURE
            should_update = True
        
        # 2. Successful recovery
        elif self._is_successful_recovery(recovery_info, outcome):
            memory_type = MemoryType.RECOVERY
            should_update = True
        
        # 3. High uncertainty
        elif self._is_high_uncertainty(confidence_before, confidence_after):
            memory_type = MemoryType.INSIGHT
            should_update = True
        
        # 4. Notable success
        elif self._is_notable_success(confidence_before, confidence_after, outcome):
            memory_type = MemoryType.SUCCESS
            should_update = True
        
        # 5. Surprising outcome
        elif self._is_surprising_outcome(confidence_before, confidence_after):
            memory_type = MemoryType.INSIGHT
            should_update = True
        
        if should_update:
            self.memory_signals += 1
        
        return should_update, memory_type
    
    def _is_novel_failure(self, failure_info: Optional[Dict[str, Any]]) -> bool:
        """Check if failure pattern is novel.
        
        Args:
            failure_info: Failure detection info
            
        Returns:
            True if novel failure pattern
        """
        if not failure_info:
            return False
        
        failure_type = failure_info.get("failure_type")
        if not failure_type or failure_type == "none":
            return False
        
        # Check if we've seen this failure type
        if failure_type not in self.seen_failure_types:
            self.seen_failure_types.add(failure_type)
            return True
        
        # Check confidence threshold
        failure_confidence = failure_info.get("confidence", 0.0)
        return failure_confidence >= self.config.confidence_threshold
    
    def _is_successful_recovery(
        self,
        recovery_info: Optional[Dict[str, Any]],
        outcome: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if recovery was successful.
        
        Args:
            recovery_info: Recovery attempt info
            outcome: Action outcome info
            
        Returns:
            True if recovery succeeded
        """
        if not recovery_info:
            return False
        
        # Recovery must be attempted
        if not recovery_info.get("attempted", False):
            return False
        
        # Recovery must succeed
        recovery_success = recovery_info.get("success", False)
        if not recovery_success:
            return False
        
        # Track novel recovery strategy
        strategy = recovery_info.get("strategy")
        if strategy and strategy not in self.seen_recovery_strategies:
            self.seen_recovery_strategies.add(strategy)
        
        return True
    
    def _is_high_uncertainty(
        self,
        confidence_before: float,
        confidence_after: float,
    ) -> bool:
        """Check if high uncertainty situation.
        
        Args:
            confidence_before: Confidence before action
            confidence_after: Confidence after action
            
        Returns:
            True if high uncertainty
        """
        # Low confidence before or after
        if (
            confidence_before < self.config.min_confidence_for_certainty
            or confidence_after < self.config.min_confidence_for_certainty
        ):
            return True
        
        # Large uncertainty increase
        confidence_delta = confidence_after - confidence_before
        if abs(confidence_delta) > self.config.uncertainty_threshold:
            return True
        
        return False
    
    def _is_notable_success(
        self,
        confidence_before: float,
        confidence_after: float,
        outcome: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if notably successful outcome.
        
        Args:
            confidence_before: Confidence before action
            confidence_after: Confidence after action
            outcome: Action outcome info
            
        Returns:
            True if notable success
        """
        if not outcome:
            return False
        
        # Must be successful
        if not outcome.get("success", False):
            return False
        
        # High confidence success
        if confidence_after >= self.config.high_confidence_threshold:
            return True
        
        # Success despite low initial confidence
        if (
            confidence_before < self.config.min_confidence_for_certainty
            and confidence_after > self.config.confidence_threshold
        ):
            return True
        
        return False
    
    def _is_surprising_outcome(
        self,
        confidence_before: float,
        confidence_after: float,
    ) -> bool:
        """Check if outcome was surprising.
        
        Args:
            confidence_before: Confidence before action
            confidence_after: Confidence after action
            
        Returns:
            True if surprising outcome
        """
        # Large confidence change in either direction
        confidence_delta = abs(confidence_after - confidence_before)
        
        return confidence_delta > 0.4  # Threshold for surprise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory signal statistics.
        
        Returns:
            Statistics dictionary
        """
        memory_rate = self.memory_signals / self.total_steps if self.total_steps > 0 else 0.0
        
        return {
            "total_steps": self.total_steps,
            "memory_signals": self.memory_signals,
            "memory_rate": memory_rate,
            "unique_failure_types": len(self.seen_failure_types),
            "unique_recovery_strategies": len(self.seen_recovery_strategies),
            "unique_action_patterns": len(self.seen_action_patterns),
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.total_steps = 0
        self.memory_signals = 0
    
    def clear_history(self) -> None:
        """Clear seen pattern history."""
        self.seen_failure_types.clear()
        self.seen_recovery_strategies.clear()
        self.seen_action_patterns.clear()
        self.reset_statistics()


def analyze_memory_patterns(
    annotations: List[Dict[str, Any]],
    config: Optional[ReflectionConfig] = None,
) -> Dict[str, Any]:
    """Analyze memory update patterns in annotations.
    
    Args:
        annotations: List of reflection annotations
        config: Reflection configuration
        
    Returns:
        Analysis results with statistics
    """
    config = config or DEFAULT_REFLECTION_CONFIG
    
    # Count memory types
    memory_counts = {
        MemoryType.SUCCESS: 0,
        MemoryType.FAILURE: 0,
        MemoryType.RECOVERY: 0,
        MemoryType.INSIGHT: 0,
        MemoryType.NONE: 0,
    }
    
    # Track confidence patterns
    confidences_before = []
    confidences_after = []
    confidence_deltas = []
    
    for annotation in annotations:
        # Count memory type
        memory_type = annotation.get("memory_type", MemoryType.NONE)
        if memory_type in memory_counts:
            memory_counts[memory_type] += 1
        
        # Track confidence
        conf_before = annotation.get("confidence_before", 0.0)
        conf_after = annotation.get("confidence_after", 0.0)
        confidences_before.append(conf_before)
        confidences_after.append(conf_after)
        confidence_deltas.append(conf_after - conf_before)
    
    # Calculate statistics
    total = len(annotations)
    memory_updates = sum(
        count
        for mem_type, count in memory_counts.items()
        if mem_type != MemoryType.NONE
    )
    
    return {
        "total_annotations": total,
        "memory_updates": memory_updates,
        "memory_rate": memory_updates / total if total > 0 else 0.0,
        "memory_type_distribution": {
            mem_type.value: count for mem_type, count in memory_counts.items()
        },
        "avg_confidence_before": sum(confidences_before) / len(confidences_before) if confidences_before else 0.0,
        "avg_confidence_after": sum(confidences_after) / len(confidences_after) if confidences_after else 0.0,
        "avg_confidence_delta": sum(confidence_deltas) / len(confidence_deltas) if confidence_deltas else 0.0,
        "min_confidence": min(confidences_before + confidences_after) if (confidences_before + confidences_after) else 0.0,
        "max_confidence": max(confidences_before + confidences_after) if (confidences_before + confidences_after) else 0.0,
    }
