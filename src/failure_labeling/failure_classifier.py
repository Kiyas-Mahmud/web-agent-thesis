"""
Failure Classification Engine

Categorizes detected failure signals into 9 failure types using rule-based
classification. Maps low-level signals to high-level failure categories.

Classification Strategy:
1. Analyze all detected signals
2. Apply classification rules with priority ordering
3. Select most likely failure type based on evidence
4. Handle cases with multiple possible classifications
"""

from typing import List, Optional, Dict, Set, Tuple
from dataclasses import dataclass

try:
    from .failure_schema import FailureType, ExecutionOutcome
    from .failure_detector import FailureSignal, SignalType
except ImportError:
    from failure_labeling.failure_schema import FailureType, ExecutionOutcome
    from failure_labeling.failure_detector import FailureSignal, SignalType


@dataclass
class ClassificationRule:
    """A rule for classifying signals into a failure type.
    
    Each rule defines:
    - Required signals that must be present
    - Optional signals that increase confidence
    - Excluded signals that disqualify this classification
    - Priority for conflict resolution
    """
    
    failure_type: FailureType
    required_signals: Set[SignalType]
    optional_signals: Set[SignalType]
    excluded_signals: Set[SignalType]
    priority: int  # Higher = checked first
    min_confidence: float = 0.5
    
    def matches(self, signals: List[FailureSignal]) -> bool:
        """Check if this rule matches the given signals.
        
        Args:
            signals: List of detected failure signals
            
        Returns:
            True if rule matches (all required present, no excluded present)
        """
        signal_types = {s.signal_type for s in signals}
        
        # Check excluded signals
        if signal_types & self.excluded_signals:
            return False
        
        # Check required signals
        if not self.required_signals.issubset(signal_types):
            return False
        
        # Check minimum confidence
        max_confidence = max((s.confidence for s in signals), default=0.0)
        if max_confidence < self.min_confidence:
            return False
        
        return True
    
    def compute_confidence(self, signals: List[FailureSignal]) -> float:
        """Compute confidence for this classification.
        
        Args:
            signals: List of detected failure signals
            
        Returns:
            Confidence score (0.0-1.0)
        """
        signal_types = {s.signal_type for s in signals}
        
        # Base confidence from required signals
        required_confidences = [
            s.confidence for s in signals
            if s.signal_type in self.required_signals
        ]
        base_confidence = sum(required_confidences) / len(self.required_signals) if self.required_signals else 0.5
        
        # Boost from optional signals
        optional_matches = len(signal_types & self.optional_signals)
        optional_boost = min(optional_matches * 0.1, 0.2)
        
        # Final confidence
        confidence = min(base_confidence + optional_boost, 1.0)
        
        return confidence


class FailureClassifier:
    """Classifies failure signals into failure types.
    
    Uses rule-based classification with priority ordering to map
    detected signals to the most appropriate failure category.
    
    Usage:
        classifier = FailureClassifier()
        failure_type, confidence = classifier.classify(signals)
    """
    
    def __init__(self):
        """Initialize classifier with classification rules."""
        self.rules = self._create_classification_rules()
    
    def _create_classification_rules(self) -> List[ClassificationRule]:
        """Create classification rules for all failure types.
        
        Returns:
            List of classification rules ordered by priority
        """
        rules = []
        
        # PERCEPTION_ERROR: Element not found, selector issues
        rules.append(ClassificationRule(
            failure_type=FailureType.PERCEPTION_ERROR,
            required_signals={SignalType.ELEMENT_NOT_FOUND},
            optional_signals={SignalType.ACTION_FAILED, SignalType.NO_VISUAL_CHANGE},
            excluded_signals=set(),
            priority=100,  # Highest priority - clear signal
            min_confidence=0.7,
        ))
        
        # TOOL_FAILURE: Browser exceptions, navigation errors
        rules.append(ClassificationRule(
            failure_type=FailureType.TOOL_FAILURE,
            required_signals={SignalType.BROWSER_EXCEPTION},
            optional_signals={SignalType.ACTION_FAILED, SignalType.NAVIGATION_ERROR},
            excluded_signals={SignalType.ELEMENT_NOT_FOUND},  # That's PERCEPTION_ERROR
            priority=95,
            min_confidence=0.6,
        ))
        
        rules.append(ClassificationRule(
            failure_type=FailureType.TOOL_FAILURE,
            required_signals={SignalType.NAVIGATION_ERROR},
            optional_signals={SignalType.BROWSER_EXCEPTION},
            excluded_signals=set(),
            priority=90,
            min_confidence=0.6,
        ))
        
        # LOOP_DETECTED: Stuck in repeated states/actions
        rules.append(ClassificationRule(
            failure_type=FailureType.LOOP_DETECTED,
            required_signals={SignalType.LOOP_DETECTED},
            optional_signals={SignalType.REPEATED_STATE, SignalType.NO_VISUAL_CHANGE},
            excluded_signals=set(),
            priority=85,
            min_confidence=0.7,
        ))
        
        # STATE_NO_CHANGE: Action produced no observable effect
        rules.append(ClassificationRule(
            failure_type=FailureType.STATE_NO_CHANGE,
            required_signals={SignalType.NO_VISUAL_CHANGE},
            optional_signals={SignalType.REPEATED_STATE},
            excluded_signals={
                SignalType.ELEMENT_NOT_FOUND,
                SignalType.BROWSER_EXCEPTION,
                SignalType.LOOP_DETECTED,  # Loop is more specific
            },
            priority=70,
            min_confidence=0.6,
        ))
        
        # ACTION_MISMATCH: Action failed or incomplete
        rules.append(ClassificationRule(
            failure_type=FailureType.ACTION_MISMATCH,
            required_signals={SignalType.ACTION_FAILED},
            optional_signals={SignalType.ACTION_INCOMPLETE, SignalType.NO_VISUAL_CHANGE},
            excluded_signals={
                SignalType.ELEMENT_NOT_FOUND,
                SignalType.BROWSER_EXCEPTION,
            },
            priority=65,
            min_confidence=0.6,
        ))
        
        rules.append(ClassificationRule(
            failure_type=FailureType.ACTION_MISMATCH,
            required_signals={SignalType.ACTION_INCOMPLETE},
            optional_signals={SignalType.MINIMAL_VISUAL_CHANGE},
            excluded_signals={
                SignalType.ELEMENT_NOT_FOUND,
                SignalType.BROWSER_EXCEPTION,
                SignalType.ACTION_FAILED,  # ACTION_FAILED is stronger
            },
            priority=60,
            min_confidence=0.5,
        ))
        
        # UI_VARIATION: Unexpected page changes, redirects
        rules.append(ClassificationRule(
            failure_type=FailureType.UI_VARIATION,
            required_signals={SignalType.UNEXPECTED_REDIRECT},
            optional_signals={SignalType.PAGE_CHANGED, SignalType.POPUP_APPEARED},
            excluded_signals=set(),
            priority=55,
            min_confidence=0.5,
        ))
        
        rules.append(ClassificationRule(
            failure_type=FailureType.UI_VARIATION,
            required_signals={SignalType.POPUP_APPEARED},
            optional_signals={SignalType.PAGE_CHANGED},
            excluded_signals=set(),
            priority=50,
            min_confidence=0.5,
        ))
        
        # GOAL_MISALIGNMENT: Timeout during execution (suggests wrong approach)
        # This is harder to detect automatically, so lower priority
        rules.append(ClassificationRule(
            failure_type=FailureType.GOAL_MISALIGNMENT,
            required_signals={SignalType.ACTION_TIMEOUT},
            optional_signals={SignalType.SLOW_EXECUTION, SignalType.REPEATED_STATE},
            excluded_signals={
                SignalType.BROWSER_EXCEPTION,
                SignalType.NAVIGATION_ERROR,
            },
            priority=40,
            min_confidence=0.4,
        ))
        
        # REASONING_ERROR: Combination of slow execution and minimal change
        # Suggests agent is making illogical choices
        rules.append(ClassificationRule(
            failure_type=FailureType.REASONING_ERROR,
            required_signals={SignalType.MINIMAL_VISUAL_CHANGE, SignalType.SLOW_EXECUTION},
            optional_signals={SignalType.REPEATED_STATE},
            excluded_signals={
                SignalType.BROWSER_EXCEPTION,
                SignalType.ELEMENT_NOT_FOUND,
            },
            priority=30,
            min_confidence=0.4,
        ))
        
        # Sort by priority (highest first)
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        return rules
    
    def classify(
        self,
        signals: List[FailureSignal],
    ) -> Tuple[FailureType, float, Optional[str]]:
        """Classify failure signals into a failure type.
        
        Args:
            signals: List of detected failure signals
            
        Returns:
            Tuple of (failure_type, confidence, explanation)
        """
        if not signals:
            return (FailureType.NONE, 1.0, "No failure signals detected")
        
        # Try each rule in priority order
        for rule in self.rules:
            if rule.matches(signals):
                confidence = rule.compute_confidence(signals)
                explanation = self._generate_explanation(rule.failure_type, signals)
                return (rule.failure_type, confidence, explanation)
        
        # No rule matched - check if signals exist but are weak
        if signals:
            max_confidence = max(s.confidence for s in signals)
            if max_confidence < 0.5:
                return (
                    FailureType.NONE,
                    0.7,
                    f"Weak failure signals detected (max confidence: {max_confidence:.2f})"
                )
            else:
                # Signals exist but don't match any rule - classify as REASONING_ERROR
                return (
                    FailureType.REASONING_ERROR,
                    0.5,
                    "Failure signals detected but don't match known patterns"
                )
        
        return (FailureType.NONE, 1.0, "No failure detected")
    
    def classify_all_candidates(
        self,
        signals: List[FailureSignal],
    ) -> List[Tuple[FailureType, float]]:
        """Get all possible failure classifications ranked by confidence.
        
        Useful for understanding ambiguous cases or generating alternative
        diagnoses.
        
        Args:
            signals: List of detected failure signals
            
        Returns:
            List of (failure_type, confidence) tuples sorted by confidence
        """
        candidates = []
        
        for rule in self.rules:
            if rule.matches(signals):
                confidence = rule.compute_confidence(signals)
                candidates.append((rule.failure_type, confidence))
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda c: c[1], reverse=True)
        
        return candidates
    
    def _generate_explanation(
        self,
        failure_type: FailureType,
        signals: List[FailureSignal],
    ) -> str:
        """Generate human-readable explanation for classification.
        
        Args:
            failure_type: Classified failure type
            signals: Supporting signals
            
        Returns:
            Explanation string
        """
        # Get primary signal
        primary = max(signals, key=lambda s: s.confidence)
        
        explanations = {
            FailureType.PERCEPTION_ERROR: (
                f"Element not found or selector mismatch. {primary.description}"
            ),
            FailureType.ACTION_MISMATCH: (
                f"Action execution failed or incomplete. {primary.description}"
            ),
            FailureType.STATE_NO_CHANGE: (
                f"Action produced no observable state change. {primary.description}"
            ),
            FailureType.LOOP_DETECTED: (
                f"Agent stuck in repeated states or actions. {primary.description}"
            ),
            FailureType.GOAL_MISALIGNMENT: (
                f"Action doesn't advance toward goal. {primary.description}"
            ),
            FailureType.TOOL_FAILURE: (
                f"Browser or tool exception occurred. {primary.description}"
            ),
            FailureType.UI_VARIATION: (
                f"Unexpected page behavior detected. {primary.description}"
            ),
            FailureType.REASONING_ERROR: (
                f"Logical error in action planning. {primary.description}"
            ),
        }
        
        return explanations.get(
            failure_type,
            f"Failure detected: {primary.description}"
        )
    
    def determine_outcome(
        self,
        failure_type: FailureType,
        confidence: float,
    ) -> ExecutionOutcome:
        """Determine execution outcome from failure type and confidence.
        
        Args:
            failure_type: Classified failure type
            confidence: Classification confidence
            
        Returns:
            Execution outcome (SUCCESS, FAILURE, PARTIAL_SUCCESS)
        """
        if failure_type == FailureType.NONE:
            return ExecutionOutcome.SUCCESS
        
        # High-confidence failures
        if confidence >= 0.7:
            return ExecutionOutcome.FAILURE
        
        # Medium-confidence or recoverable failures
        if confidence >= 0.5 or failure_type in {
            FailureType.UI_VARIATION,
            FailureType.STATE_NO_CHANGE,
        }:
            return ExecutionOutcome.PARTIAL_SUCCESS
        
        # Low confidence
        return ExecutionOutcome.PARTIAL_SUCCESS
    
    def assess_severity(self, failure_type: FailureType) -> str:
        """Assess severity level of failure type.
        
        Args:
            failure_type: Failure type
            
        Returns:
            Severity level: 'low', 'medium', 'high'
        """
        severity_map = {
            FailureType.NONE: "low",
            FailureType.UI_VARIATION: "low",
            FailureType.STATE_NO_CHANGE: "medium",
            FailureType.ACTION_MISMATCH: "medium",
            FailureType.GOAL_MISALIGNMENT: "medium",
            FailureType.REASONING_ERROR: "medium",
            FailureType.PERCEPTION_ERROR: "high",
            FailureType.LOOP_DETECTED: "high",
            FailureType.TOOL_FAILURE: "high",
        }
        return severity_map.get(failure_type, "medium")
    
    def assess_recoverability(self, failure_type: FailureType) -> bool:
        """Assess if failure type is potentially recoverable.
        
        Args:
            failure_type: Failure type
            
        Returns:
            True if likely recoverable
        """
        recoverable_types = {
            FailureType.NONE,
            FailureType.UI_VARIATION,
            FailureType.STATE_NO_CHANGE,
            FailureType.ACTION_MISMATCH,
            FailureType.PERCEPTION_ERROR,  # Can try different selector
        }
        return failure_type in recoverable_types
