"""
Reflection Generator

Generates natural language reflection texts that explain:
- What action was attempted
- What the expected outcome was
- What actually happened
- Why it succeeded or failed
- What recovery strategy was used (if any)
"""

from typing import Dict, Any, Optional
from enum import Enum

try:
    from .reflection_schema import ReflectionConfig, DEFAULT_REFLECTION_CONFIG
except ImportError:
    from reflection_annotation.reflection_schema import ReflectionConfig, DEFAULT_REFLECTION_CONFIG


class ReflectionTemplate(str, Enum):
    """Templates for different reflection scenarios."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    UNCERTAINTY = "uncertainty"
    RECOVERY = "recovery"
    LOOP = "loop"
    TIMEOUT = "timeout"


class ReflectionGenerator:
    """Generates natural language reflection texts.
    
    Uses template-based generation with dynamic value insertion.
    """
    
    def __init__(self, config: Optional[ReflectionConfig] = None):
        """Initialize reflection generator.
        
        Args:
            config: Reflection configuration
        """
        self.config = config or DEFAULT_REFLECTION_CONFIG
    
    def generate_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]] = None,
        recovery_info: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate reflection text for a step.
        
        Args:
            action: Action that was performed
            outcome: Outcome information
            failure_info: Failure detection info (from Task-04)
            recovery_info: Recovery attempt info (from Task-05)
            metrics: Visual/state metrics (from Task-03)
            
        Returns:
            Natural language reflection text
        """
        # Determine template based on outcome
        template = self._select_template(outcome, failure_info, recovery_info)
        
        # Generate reflection based on template
        if template == ReflectionTemplate.SUCCESS:
            text = self._generate_success_reflection(action, outcome, metrics)
        elif template == ReflectionTemplate.FAILURE:
            text = self._generate_failure_reflection(action, outcome, failure_info, metrics)
        elif template == ReflectionTemplate.RECOVERY:
            text = self._generate_recovery_reflection(action, outcome, recovery_info, metrics)
        elif template == ReflectionTemplate.LOOP:
            text = self._generate_loop_reflection(action, outcome, metrics)
        elif template == ReflectionTemplate.TIMEOUT:
            text = self._generate_timeout_reflection(action, outcome)
        else:  # UNCERTAINTY
            text = self._generate_uncertainty_reflection(action, outcome, metrics)
        
        # Truncate if needed
        if len(text) > self.config.max_reflection_length:
            text = text[:self.config.max_reflection_length - 3] + "..."
        
        return text
    
    def _select_template(
        self,
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]],
        recovery_info: Optional[Dict[str, Any]],
    ) -> ReflectionTemplate:
        """Select appropriate template for the situation.
        
        Args:
            outcome: Outcome information
            failure_info: Failure detection info
            recovery_info: Recovery attempt info
            
        Returns:
            Selected template
        """
        # Recovery template if recovery was attempted
        if recovery_info and recovery_info.get("attempted"):
            return ReflectionTemplate.RECOVERY
        
        # Timeout template if action timed out
        if outcome.get("timeout", False):
            return ReflectionTemplate.TIMEOUT
        
        # Loop template if loop detected
        if outcome.get("loop_detected", False):
            return ReflectionTemplate.LOOP
        
        # Failure template if failure detected
        if failure_info and failure_info.get("failure_type") not in [None, "none"]:
            return ReflectionTemplate.FAILURE
        
        # Success template if clear success indicators
        if outcome.get("success", False):
            return ReflectionTemplate.SUCCESS
        
        # Uncertainty template if ambiguous
        return ReflectionTemplate.UNCERTAINTY
    
    def _generate_success_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Generate reflection for successful action.
        
        Args:
            action: Action information
            outcome: Outcome information
            metrics: Visual/state metrics
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        target = action.get("target", "element")
        
        # Base success message
        text = f"Successfully {action_type} on {target}. "
        
        # Add outcome details
        if outcome.get("state_changed"):
            text += "State changed as expected. "
        
        # Add metrics if configured
        if self.config.include_metrics and metrics:
            visual_diff = metrics.get("visual", {}).get("pixel_diff", 0)
            if visual_diff > 0:
                text += f"Visual change detected (diff={visual_diff:.2f}). "
        
        # Add confidence note
        confidence = outcome.get("confidence", 0.8)
        if confidence > 0.9:
            text += "High confidence in success."
        else:
            text += "Moderate confidence in success."
        
        return text
    
    def _generate_failure_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        failure_info: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Generate reflection for failed action.
        
        Args:
            action: Action information
            outcome: Outcome information
            failure_info: Failure detection info
            metrics: Visual/state metrics
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        target = action.get("target", "element")
        
        # Base failure message
        text = f"Failed to {action_type} on {target}. "
        
        # Add failure type if available
        if failure_info:
            failure_type = failure_info.get("failure_type", "unknown")
            text += f"Diagnosed as {failure_type.upper().replace('_', ' ')}. "
            
            # Add primary signal
            primary_signal = failure_info.get("primary_signal")
            if primary_signal:
                text += f"Primary signal: {primary_signal.replace('_', ' ')}. "
        
        # Add metrics if configured
        if self.config.include_metrics and metrics:
            visual_diff = metrics.get("visual", {}).get("pixel_diff", 0)
            if visual_diff < 0.05:
                text += "No significant state change detected. "
            else:
                text += f"Some visual change detected (diff={visual_diff:.2f}) but unclear outcome. "
        
        return text
    
    def _generate_recovery_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        recovery_info: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Generate reflection for recovery attempt.
        
        Args:
            action: Action information
            outcome: Outcome information
            recovery_info: Recovery attempt info
            metrics: Visual/state metrics
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        target = action.get("target", "element")
        
        # Base message about original failure
        text = f"Attempted {action_type} on {target} but failed. "
        
        # Add recovery strategy
        if recovery_info:
            strategy = recovery_info.get("strategy", "unknown")
            text += f"Attempting {strategy.upper().replace('_', ' ')} recovery. "
            
            # Add recovery outcome
            if recovery_info.get("success"):
                text += "Recovery succeeded. "
            else:
                text += "Recovery failed. "
                
                # Add next strategy if available
                next_strategy = recovery_info.get("next_strategy")
                if next_strategy:
                    text += f"Will try {next_strategy.upper().replace('_', ' ')} next. "
        
        return text
    
    def _generate_loop_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Generate reflection for loop detection.
        
        Args:
            action: Action information
            outcome: Outcome information
            metrics: Visual/state metrics
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        
        text = f"Loop detected after {action_type}. "
        text += "Agent appears to be repeating same actions without making progress. "
        
        # Add loop details if available
        loop_info = outcome.get("loop_info", {})
        loop_size = loop_info.get("size", 0)
        if loop_size > 0:
            text += f"Repeating cycle of {loop_size} steps. "
        
        text += "Backtracking recommended."
        
        return text
    
    def _generate_timeout_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> str:
        """Generate reflection for timeout.
        
        Args:
            action: Action information
            outcome: Outcome information
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        target = action.get("target", "element")
        
        text = f"Action {action_type} on {target} timed out. "
        
        timeout_duration = outcome.get("timeout_duration", 30)
        text += f"Exceeded {timeout_duration}s limit. "
        
        text += "Possible causes: page not responding, network issues, or wrong element. "
        text += "Retry recommended."
        
        return text
    
    def _generate_uncertainty_reflection(
        self,
        action: Dict[str, Any],
        outcome: Dict[str, Any],
        metrics: Optional[Dict[str, Any]],
    ) -> str:
        """Generate reflection for uncertain outcome.
        
        Args:
            action: Action information
            outcome: Outcome information
            metrics: Visual/state metrics
            
        Returns:
            Reflection text
        """
        action_type = action.get("type", "action")
        target = action.get("target", "element")
        
        text = f"Uncertain about outcome of {action_type} on {target}. "
        
        # Add what we observed
        if metrics:
            visual_diff = metrics.get("visual", {}).get("pixel_diff", 0)
            state_changed = metrics.get("state_hash", {}).get("changed", False)
            
            if visual_diff > 0.1:
                text += "Visual change detected "
            if state_changed:
                text += "and state changed "
            
            text += "but unclear if goal was achieved. "
        else:
            text += "Unable to determine success. "
        
        # Add confidence
        confidence = outcome.get("confidence", 0.5)
        text += f"Confidence: {confidence:.2f}. "
        
        return text


def format_action_description(action: Dict[str, Any]) -> str:
    """Format action as human-readable description.
    
    Args:
        action: Action information
        
    Returns:
        Formatted action description
    """
    action_type = action.get("type", "action")
    
    # Format based on action type
    if action_type == "click":
        target = action.get("target", "element")
        return f"clicked on {target}"
    
    elif action_type == "type":
        target = action.get("target", "input")
        text = action.get("text", "...")
        # Truncate long text
        if len(text) > 30:
            text = text[:27] + "..."
        return f"typed '{text}' into {target}"
    
    elif action_type == "navigate":
        url = action.get("url", "page")
        return f"navigated to {url}"
    
    elif action_type == "scroll":
        direction = action.get("direction", "down")
        return f"scrolled {direction}"
    
    elif action_type == "select":
        target = action.get("target", "dropdown")
        value = action.get("value", "option")
        return f"selected '{value}' from {target}"
    
    elif action_type == "wait":
        duration = action.get("duration", 0)
        return f"waited {duration}ms"
    
    else:
        return f"performed {action_type}"
