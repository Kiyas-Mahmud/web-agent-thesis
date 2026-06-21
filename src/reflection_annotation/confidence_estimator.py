"""
Confidence Estimator

Estimates agent confidence before and after actions based on:
- Element visibility and detection
- Action execution history
- Page complexity
- Previous failure rates
- Visual/state metrics
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from .reflection_schema import ReflectionConfig, DEFAULT_REFLECTION_CONFIG
except ImportError:
    from reflection_annotation.reflection_schema import ReflectionConfig, DEFAULT_REFLECTION_CONFIG


@dataclass
class ConfidenceFactors:
    """Factors that influence confidence estimation.
    
    Captures all the information used to calculate confidence scores.
    """
    
    # Element detection
    element_found: bool = True
    element_visibility: float = 1.0  # 0.0 to 1.0
    selector_confidence: float = 1.0  # 0.0 to 1.0
    
    # Action history
    recent_successes: int = 0
    recent_failures: int = 0
    action_success_rate: float = 0.0  # Historical success rate
    
    # Page state
    page_complexity: float = 0.5  # 0.0 (simple) to 1.0 (complex)
    page_loaded: bool = True
    page_stable: bool = True
    
    # Timing
    time_since_last_success: float = 0.0  # seconds
    action_timeout: bool = False
    
    # Visual/state metrics
    visual_change_detected: bool = False
    state_change_detected: bool = False
    loop_detected: bool = False
    
    # Failure info (from Task-04)
    failure_type: Optional[str] = None
    failure_severity: float = 0.0  # 0.0 to 1.0
    failure_confidence: float = 0.0  # 0.0 to 1.0
    
    # Recovery info (from Task-05)
    recovery_attempted: bool = False
    recovery_success: bool = False
    recovery_strategy: Optional[str] = None


class ConfidenceEstimator:
    """Estimates agent confidence for actions.
    
    Uses heuristic-based scoring adjusted by various factors.
    """
    
    def __init__(self, config: Optional[ReflectionConfig] = None):
        """Initialize confidence estimator.
        
        Args:
            config: Reflection configuration
        """
        self.config = config or DEFAULT_REFLECTION_CONFIG
        
        # Track history for adaptive confidence
        self.action_history: List[bool] = []  # Success/failure history
        self.max_history = 20  # Keep last N actions
    
    def estimate_before_action(
        self,
        factors: ConfidenceFactors,
    ) -> float:
        """Estimate confidence before executing action.
        
        This is the agent's belief about whether the action will succeed.
        
        Args:
            factors: Confidence factors
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = self.config.base_confidence
        
        # Element detection factors
        if not factors.element_found:
            confidence -= self.config.element_not_found_penalty
        else:
            # Adjust by visibility
            if factors.element_visibility < 0.5:
                confidence -= 0.2
            elif factors.element_visibility < 0.8:
                confidence -= 0.1
            
            # Adjust by selector confidence
            confidence *= factors.selector_confidence
        
        # Action history
        if factors.recent_failures > 2:
            confidence -= self.config.recent_failure_penalty
        elif factors.recent_failures > 0:
            confidence -= 0.1
        
        # Success rate
        if factors.action_success_rate > 0:
            # Blend with historical success rate
            confidence = 0.7 * confidence + 0.3 * factors.action_success_rate
        
        # Page state
        if not factors.page_loaded or not factors.page_stable:
            confidence -= 0.15
        
        if factors.page_complexity > 0.7:
            confidence -= self.config.high_complexity_penalty
        
        # Timing
        if factors.time_since_last_success > 30:  # 30 seconds
            confidence -= 0.1
        
        # Loop detection
        if factors.loop_detected:
            confidence -= 0.25  # Significant penalty for loops
        
        # Ensure bounds
        return max(0.0, min(1.0, confidence))
    
    def estimate_after_action(
        self,
        factors: ConfidenceFactors,
        confidence_before: float,
    ) -> float:
        """Estimate confidence after observing action outcome.
        
        This reflects whether the agent believes the action succeeded.
        
        Args:
            factors: Confidence factors (including outcome info)
            confidence_before: Pre-action confidence
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = confidence_before
        
        # Visual/state changes
        if factors.visual_change_detected and factors.state_change_detected:
            # Both visual and state changed - likely success
            confidence = min(1.0, confidence + 0.15)
        elif factors.visual_change_detected or factors.state_change_detected:
            # One changed - possible success
            confidence = min(1.0, confidence + 0.05)
        else:
            # No change detected - likely failure
            confidence = max(0.0, confidence - 0.3)
        
        # Timeout
        if factors.action_timeout:
            confidence = max(0.0, confidence - 0.2)
        
        # Failure detection
        if factors.failure_type and factors.failure_type != "none":
            # Reduce confidence based on failure severity
            confidence = max(0.0, confidence - factors.failure_severity * 0.4)
        
        # Recovery
        if factors.recovery_attempted:
            if factors.recovery_success:
                # Successful recovery increases confidence
                confidence = min(1.0, confidence + 0.2)
            else:
                # Failed recovery decreases confidence
                confidence = max(0.0, confidence - 0.2)
        
        # Loop detection
        if factors.loop_detected:
            confidence = max(0.0, confidence - 0.3)
        
        # Ensure bounds
        return max(0.0, min(1.0, confidence))
    
    def update_history(self, success: bool) -> None:
        """Update action history for adaptive confidence.
        
        Args:
            success: Whether the action succeeded
        """
        self.action_history.append(success)
        
        # Keep only recent history
        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)
    
    def get_recent_success_rate(self, window: int = 5) -> float:
        """Get success rate over recent actions.
        
        Args:
            window: Number of recent actions to consider
            
        Returns:
            Success rate (0.0-1.0)
        """
        if not self.action_history:
            return 0.0
        
        recent = self.action_history[-window:]
        return sum(recent) / len(recent)
    
    def get_recent_failures(self, window: int = 5) -> int:
        """Count recent failed actions.
        
        Args:
            window: Number of recent actions to consider
            
        Returns:
            Number of failures
        """
        if not self.action_history:
            return 0
        
        recent = self.action_history[-window:]
        return len([s for s in recent if not s])
    
    def reset_history(self) -> None:
        """Reset action history."""
        self.action_history = []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get confidence estimation statistics.
        
        Returns:
            Statistics dictionary
        """
        total_actions = len(self.action_history)
        if total_actions == 0:
            return {
                "total_actions": 0,
                "success_rate": 0.0,
                "recent_success_rate": 0.0,
                "recent_failures": 0,
            }
        
        success_count = sum(self.action_history)
        success_rate = success_count / total_actions
        
        return {
            "total_actions": total_actions,
            "success_rate": success_rate,
            "recent_success_rate": self.get_recent_success_rate(),
            "recent_failures": self.get_recent_failures(),
        }


def estimate_element_visibility(element_info: Dict[str, Any]) -> float:
    """Estimate visibility of an element.
    
    Args:
        element_info: Element information (bounds, attributes, etc.)
        
    Returns:
        Visibility score (0.0-1.0)
    """
    if not element_info:
        return 0.0
    
    visibility = 1.0
    
    # Check if element has bounds
    bounds = element_info.get("bounds")
    if bounds:
        width = bounds.get("width", 0)
        height = bounds.get("height", 0)
        
        # Very small elements are hard to interact with
        if width < 10 or height < 10:
            visibility *= 0.5
    
    # Check visibility attributes
    if element_info.get("hidden", False):
        return 0.0
    
    if element_info.get("display") == "none":
        return 0.0
    
    opacity = element_info.get("opacity", 1.0)
    visibility *= opacity
    
    # Check if element is in viewport
    in_viewport = element_info.get("in_viewport", True)
    if not in_viewport:
        visibility *= 0.7
    
    return visibility


def estimate_page_complexity(page_info: Dict[str, Any]) -> float:
    """Estimate complexity of a page.
    
    Args:
        page_info: Page information (element count, DOM depth, etc.)
        
    Returns:
        Complexity score (0.0-1.0)
    """
    complexity = 0.0
    
    # Element count
    element_count = page_info.get("element_count", 0)
    if element_count > 1000:
        complexity += 0.4
    elif element_count > 500:
        complexity += 0.3
    elif element_count > 200:
        complexity += 0.2
    else:
        complexity += 0.1
    
    # DOM depth
    dom_depth = page_info.get("dom_depth", 0)
    if dom_depth > 20:
        complexity += 0.3
    elif dom_depth > 15:
        complexity += 0.2
    else:
        complexity += 0.1
    
    # Iframe count
    iframe_count = page_info.get("iframe_count", 0)
    if iframe_count > 0:
        complexity += 0.2
    
    # Dynamic content (SPAs)
    if page_info.get("is_spa", False):
        complexity += 0.2
    
    return min(1.0, complexity)


def calculate_selector_confidence(
    selector: str,
    matches_found: int,
    expected_matches: int = 1,
) -> float:
    """Calculate confidence in a CSS selector.
    
    Args:
        selector: CSS selector string
        matches_found: Number of matches found
        expected_matches: Expected number of matches
        
    Returns:
        Selector confidence (0.0-1.0)
    """
    if matches_found == 0:
        return 0.0
    
    if matches_found > expected_matches * 3:
        # Too many matches - selector may be too generic
        return 0.4
    
    if matches_found > expected_matches:
        # More matches than expected
        return 0.7
    
    if matches_found == expected_matches:
        # Exact match count
        return 1.0
    
    # Fewer matches than expected (but some found)
    return 0.8
