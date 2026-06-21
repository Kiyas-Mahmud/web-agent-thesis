"""
Failure Detection Engine

Detects failure signals from action logs, visual metrics, state hashes,
and performance data. Identifies potential failures before classification.

Detection Categories:
- Visual: No observable state change after action
- State: Loop detection via state hashing
- Performance: Timeouts and slow execution
- Exceptions: Browser errors and tool failures
- Perception: Element not found errors
- Action: Action execution mismatches
"""

from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from ..metric_computation.metric_schema import (
        StepMetrics,
        VisualMetrics,
        StateHashMetrics,
        PerformanceMetrics,
        ChangeLevel,
    )
except ImportError:
    from metric_computation.metric_schema import (
        StepMetrics,
        VisualMetrics,
        StateHashMetrics,
        PerformanceMetrics,
        ChangeLevel,
    )

try:
    from .failure_schema import DiagnosticConfig, DEFAULT_DIAGNOSTIC_CONFIG
except ImportError:
    from failure_labeling.failure_schema import DiagnosticConfig, DEFAULT_DIAGNOSTIC_CONFIG


class SignalType(str, Enum):
    """Types of failure signals that can be detected."""
    
    # Visual signals
    NO_VISUAL_CHANGE = "no_visual_change"
    MINIMAL_VISUAL_CHANGE = "minimal_visual_change"
    
    # State signals
    LOOP_DETECTED = "loop_detected"
    REPEATED_STATE = "repeated_state"
    
    # Performance signals
    ACTION_TIMEOUT = "action_timeout"
    SLOW_EXECUTION = "slow_execution"
    
    # Exception signals
    BROWSER_EXCEPTION = "browser_exception"
    ELEMENT_NOT_FOUND = "element_not_found"
    NAVIGATION_ERROR = "navigation_error"
    
    # Action signals
    ACTION_FAILED = "action_failed"
    ACTION_INCOMPLETE = "action_incomplete"
    
    # UI signals
    UNEXPECTED_REDIRECT = "unexpected_redirect"
    POPUP_APPEARED = "popup_appeared"
    PAGE_CHANGED = "page_changed"


@dataclass
class FailureSignal:
    """A detected failure signal with supporting data.
    
    Represents a single piece of evidence that suggests a failure occurred.
    Multiple signals are aggregated to form a complete failure diagnosis.
    """
    
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    source: str  # Where signal came from (e.g., 'visual_metrics')
    value: Any  # Measured value
    expected: Optional[Any] = None  # Expected value if applicable
    description: str = ""
    
    def __post_init__(self):
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")


class FailureDetector:
    """Detects failure signals from metrics and action logs.
    
    Analyzes visual changes, state transitions, performance metrics,
    and exceptions to identify potential failures.
    
    Usage:
        detector = FailureDetector(config)
        signals = detector.detect_all_signals(step_metrics, action_log)
    """
    
    def __init__(self, config: Optional[DiagnosticConfig] = None):
        """Initialize failure detector.
        
        Args:
            config: Diagnostic configuration (uses default if not provided)
        """
        self.config = config or DEFAULT_DIAGNOSTIC_CONFIG
    
    def detect_all_signals(
        self,
        step_metrics: Optional[StepMetrics],
        action_log: Dict[str, Any],
        previous_url: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> List[FailureSignal]:
        """Detect all failure signals for a step.
        
        Args:
            step_metrics: Computed metrics for the step
            action_log: Action execution log with status and errors
            previous_url: URL before action
            current_url: URL after action
            
        Returns:
            List of detected failure signals
        """
        signals = []
        
        # Detect visual change signals
        if step_metrics and step_metrics.visual:
            signals.extend(self._detect_visual_signals(step_metrics.visual))
        
        # Detect state/loop signals
        if step_metrics and step_metrics.state_hash:
            signals.extend(self._detect_state_signals(step_metrics.state_hash))
        
        # Detect performance signals
        if step_metrics and step_metrics.performance:
            signals.extend(self._detect_performance_signals(step_metrics.performance))
        
        # Detect exception signals
        signals.extend(self._detect_exception_signals(action_log))
        
        # Detect UI variation signals
        if previous_url and current_url:
            signals.extend(self._detect_ui_signals(previous_url, current_url))
        
        return signals
    
    def _detect_visual_signals(self, visual_metrics: VisualMetrics) -> List[FailureSignal]:
        """Detect visual change-related signals.
        
        Args:
            visual_metrics: Visual metrics from screenshot comparison
            
        Returns:
            List of visual-related signals
        """
        signals = []
        
        # Check for no visual change
        if visual_metrics.change_level == ChangeLevel.NO_CHANGE:
            confidence = 1.0 - visual_metrics.pixel_diff_score
            signals.append(FailureSignal(
                signal_type=SignalType.NO_VISUAL_CHANGE,
                confidence=min(confidence, 0.9),  # Cap at 0.9
                source="visual_metrics",
                value=visual_metrics.pixel_diff_score,
                expected=self.config.min_visual_change,
                description=f"No visual change detected (pixel_diff={visual_metrics.pixel_diff_score:.3f})"
            ))
        
        # Check for minimal visual change
        elif visual_metrics.change_level == ChangeLevel.MINOR_CHANGE:
            if visual_metrics.pixel_diff_score < self.config.min_visual_change * 2:
                confidence = 0.5 + (1.0 - visual_metrics.pixel_diff_score) * 0.3
                signals.append(FailureSignal(
                    signal_type=SignalType.MINIMAL_VISUAL_CHANGE,
                    confidence=min(confidence, 0.7),
                    source="visual_metrics",
                    value=visual_metrics.pixel_diff_score,
                    expected=self.config.min_visual_change * 2,
                    description=f"Minimal visual change (pixel_diff={visual_metrics.pixel_diff_score:.3f})"
                ))
        
        # Check SSIM for structural similarity (high SSIM = no change)
        if visual_metrics.ssim_score and visual_metrics.ssim_score > self.config.ssim_threshold:
            confidence = (visual_metrics.ssim_score - self.config.ssim_threshold) / (1.0 - self.config.ssim_threshold)
            signals.append(FailureSignal(
                signal_type=SignalType.NO_VISUAL_CHANGE,
                confidence=min(confidence * 0.8, 0.8),  # Lower confidence from SSIM alone
                source="visual_metrics_ssim",
                value=visual_metrics.ssim_score,
                expected=self.config.ssim_threshold,
                description=f"High structural similarity (SSIM={visual_metrics.ssim_score:.3f})"
            ))
        
        return signals
    
    def _detect_state_signals(self, state_metrics: StateHashMetrics) -> List[FailureSignal]:
        """Detect state-related signals (loops, repeated states).
        
        Args:
            state_metrics: State hash and loop detection metrics
            
        Returns:
            List of state-related signals
        """
        signals = []
        
        if not self.config.enable_loop_detection:
            return signals
        
        # Check for detected loop
        if state_metrics.loop_detected:
            signals.append(FailureSignal(
                signal_type=SignalType.LOOP_DETECTED,
                confidence=0.9,  # High confidence when loop is detected
                source="state_hash_metrics",
                value=True,
                description="Loop detected in state sequence"
            ))
        
        # Check for repeated state (seen before but not necessarily a loop)
        if state_metrics.state_occurrences and state_metrics.state_occurrences > 1:
            # Higher confidence for more repetitions
            confidence = min(0.5 + (state_metrics.state_occurrences - 1) * 0.1, 0.8)
            signals.append(FailureSignal(
                signal_type=SignalType.REPEATED_STATE,
                confidence=confidence,
                source="state_hash_metrics",
                value=state_metrics.state_occurrences,
                description=f"State repeated {state_metrics.state_occurrences} times"
            ))
        
        return signals
    
    def _detect_performance_signals(self, perf_metrics: PerformanceMetrics) -> List[FailureSignal]:
        """Detect performance-related signals (timeouts, slow execution).
        
        Args:
            perf_metrics: Performance timing metrics
            
        Returns:
            List of performance-related signals
        """
        signals = []
        
        # Check for action timeout
        if perf_metrics.execution_time_ms and perf_metrics.execution_time_ms > self.config.action_timeout_ms:
            confidence = min(
                0.7 + (perf_metrics.execution_time_ms - self.config.action_timeout_ms) / self.config.action_timeout_ms * 0.3,
                0.95
            )
            signals.append(FailureSignal(
                signal_type=SignalType.ACTION_TIMEOUT,
                confidence=confidence,
                source="performance_metrics",
                value=perf_metrics.execution_time_ms,
                expected=self.config.action_timeout_ms,
                description=f"Action exceeded timeout ({perf_metrics.execution_time_ms:.0f}ms)"
            ))
        
        # Check for slow execution (not timeout but unusually slow)
        elif perf_metrics.execution_time_ms and perf_metrics.execution_time_ms > self.config.action_timeout_ms * 0.7:
            confidence = 0.4 + (perf_metrics.execution_time_ms / self.config.action_timeout_ms) * 0.2
            signals.append(FailureSignal(
                signal_type=SignalType.SLOW_EXECUTION,
                confidence=min(confidence, 0.6),
                source="performance_metrics",
                value=perf_metrics.execution_time_ms,
                expected=self.config.action_timeout_ms * 0.5,
                description=f"Slow execution ({perf_metrics.execution_time_ms:.0f}ms)"
            ))
        
        # Check total step time
        if perf_metrics.total_step_time_ms and perf_metrics.total_step_time_ms > self.config.step_timeout_ms:
            confidence = 0.8
            signals.append(FailureSignal(
                signal_type=SignalType.ACTION_TIMEOUT,
                confidence=confidence,
                source="performance_metrics_total",
                value=perf_metrics.total_step_time_ms,
                expected=self.config.step_timeout_ms,
                description=f"Step exceeded timeout ({perf_metrics.total_step_time_ms:.0f}ms)"
            ))
        
        return signals
    
    def _detect_exception_signals(self, action_log: Dict[str, Any]) -> List[FailureSignal]:
        """Detect exception and error signals from action log.
        
        Args:
            action_log: Action execution log
            
        Returns:
            List of exception-related signals
        """
        signals = []
        
        if not self.config.treat_exceptions_as_failure:
            return signals
        
        # Check for explicit failure status
        status = action_log.get("status", "").lower()
        if status == "failed" or status == "error":
            signals.append(FailureSignal(
                signal_type=SignalType.ACTION_FAILED,
                confidence=0.95,
                source="action_log",
                value=status,
                description=f"Action status: {status}"
            ))
        
        # Check for error message
        error = action_log.get("error")
        if error:
            error_str = str(error).lower()
            
            # Element not found errors
            if any(phrase in error_str for phrase in ["not found", "no such element", "timeout", "selector"]):
                signals.append(FailureSignal(
                    signal_type=SignalType.ELEMENT_NOT_FOUND,
                    confidence=0.9,
                    source="action_log_error",
                    value=error,
                    description=f"Element not found: {error}"
                ))
            
            # Navigation errors
            elif any(phrase in error_str for phrase in ["navigation", "net::", "dns", "refused"]):
                signals.append(FailureSignal(
                    signal_type=SignalType.NAVIGATION_ERROR,
                    confidence=0.85,
                    source="action_log_error",
                    value=error,
                    description=f"Navigation error: {error}"
                ))
            
            # Generic browser exception
            else:
                signals.append(FailureSignal(
                    signal_type=SignalType.BROWSER_EXCEPTION,
                    confidence=0.8,
                    source="action_log_error",
                    value=error,
                    description=f"Browser exception: {error}"
                ))
        
        # Check for incomplete action
        if action_log.get("completed", True) is False:
            signals.append(FailureSignal(
                signal_type=SignalType.ACTION_INCOMPLETE,
                confidence=0.7,
                source="action_log",
                value=False,
                expected=True,
                description="Action did not complete fully"
            ))
        
        return signals
    
    def _detect_ui_signals(self, previous_url: str, current_url: str) -> List[FailureSignal]:
        """Detect UI variation signals (redirects, popups, page changes).
        
        Args:
            previous_url: URL before action
            current_url: URL after action
            
        Returns:
            List of UI-related signals
        """
        signals = []
        
        # Check for unexpected navigation
        if previous_url != current_url:
            # Parse URLs to check if it's a meaningful change
            prev_domain = self._extract_domain(previous_url)
            curr_domain = self._extract_domain(current_url)
            
            # Different domain = redirect
            if prev_domain != curr_domain:
                signals.append(FailureSignal(
                    signal_type=SignalType.UNEXPECTED_REDIRECT,
                    confidence=0.6,  # Medium confidence - could be intentional
                    source="url_comparison",
                    value=current_url,
                    expected=previous_url,
                    description=f"Redirected from {prev_domain} to {curr_domain}"
                ))
            
            # Same domain but different page
            else:
                signals.append(FailureSignal(
                    signal_type=SignalType.PAGE_CHANGED,
                    confidence=0.4,  # Lower confidence - often intentional
                    source="url_comparison",
                    value=current_url,
                    expected=previous_url,
                    description=f"Page changed: {previous_url} -> {current_url}"
                ))
        
        return signals
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL for comparison.
        
        Args:
            url: Full URL
            
        Returns:
            Domain portion of URL
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return url
    
    def has_failure_signals(self, signals: List[FailureSignal]) -> bool:
        """Check if there are any significant failure signals.
        
        Args:
            signals: List of detected signals
            
        Returns:
            True if there are signals suggesting failure
        """
        if not signals:
            return False
        
        # Check for high-confidence signals
        high_confidence_signals = [s for s in signals if s.confidence >= 0.7]
        if high_confidence_signals:
            return True
        
        # Check for multiple medium-confidence signals
        medium_confidence_signals = [s for s in signals if s.confidence >= 0.5]
        if len(medium_confidence_signals) >= 2:
            return True
        
        return False
    
    def get_primary_signal(self, signals: List[FailureSignal]) -> Optional[FailureSignal]:
        """Get the primary (highest confidence) signal.
        
        Args:
            signals: List of detected signals
            
        Returns:
            Signal with highest confidence, or None if no signals
        """
        if not signals:
            return None
        return max(signals, key=lambda s: s.confidence)
