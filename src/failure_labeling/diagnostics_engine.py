"""
Diagnostics Engine

Aggregates evidence from multiple sources and computes confidence scores
to produce complete failure diagnoses. Combines detection signals with
classification results to generate comprehensive failure labels.

Process:
1. Collect failure signals from detector
2. Classify signals into failure type
3. Convert signals to evidence records
4. Compute aggregate confidence
5. Assign severity and recoverability
6. Generate complete FailureLabel
"""

from typing import List, Optional

try:
    from .failure_schema import (
        FailureType,
        ExecutionOutcome,
        FailureEvidence,
        FailureLabel,
        DiagnosticConfig,
        DEFAULT_DIAGNOSTIC_CONFIG,
        create_failure_label,
        create_success_label,
    )
    from .failure_detector import FailureSignal
    from .failure_classifier import FailureClassifier
except ImportError:
    from failure_labeling.failure_schema import (
        FailureType,
        ExecutionOutcome,
        FailureEvidence,
        FailureLabel,
        DiagnosticConfig,
        DEFAULT_DIAGNOSTIC_CONFIG,
        create_failure_label,
        create_success_label,
    )
    from failure_labeling.failure_detector import FailureSignal
    from failure_labeling.failure_classifier import FailureClassifier


class EvidenceAggregator:
    """Aggregates failure signals into structured evidence.
    
    Converts low-level signals into evidence records with proper
    formatting and confidence scores.
    """
    
    @staticmethod
    def aggregate_evidence(signals: List[FailureSignal]) -> List[FailureEvidence]:
        """Convert signals to evidence records.
        
        Args:
            signals: List of detected failure signals
            
        Returns:
            List of evidence records
        """
        evidence = []
        
        for signal in signals:
            evidence.append(FailureEvidence(
                signal_type=signal.signal_type.value,
                source=signal.source,
                value=signal.value,
                expected=signal.expected,
                confidence=signal.confidence,
                description=signal.description,
            ))
        
        return evidence
    
    @staticmethod
    def compute_aggregate_confidence(
        signals: List[FailureSignal],
        classification_confidence: float,
        require_multiple: bool = False,
    ) -> float:
        """Compute aggregate confidence from signals and classification.
        
        Combines individual signal confidences with classification confidence
        to produce overall diagnostic confidence.
        
        Args:
            signals: List of detected signals
            classification_confidence: Confidence from classification
            require_multiple: Whether to require multiple signals for high confidence
            
        Returns:
            Aggregate confidence (0.0-1.0)
        """
        if not signals:
            return 0.0
        
        # Get top 3 signal confidences
        signal_confidences = sorted(
            [s.confidence for s in signals],
            reverse=True
        )[:3]
        
        # Weighted average of signal confidences
        if len(signal_confidences) == 1:
            signal_conf = signal_confidences[0]
        elif len(signal_confidences) == 2:
            signal_conf = signal_confidences[0] * 0.7 + signal_confidences[1] * 0.3
        else:
            signal_conf = (
                signal_confidences[0] * 0.6 +
                signal_confidences[1] * 0.25 +
                signal_confidences[2] * 0.15
            )
        
        # Combine with classification confidence
        # Give more weight to classification if signals are weak
        if signal_conf >= 0.7:
            aggregate = signal_conf * 0.7 + classification_confidence * 0.3
        else:
            aggregate = signal_conf * 0.5 + classification_confidence * 0.5
        
        # Penalty for single signal if require_multiple is True
        if require_multiple and len(signals) == 1:
            aggregate *= 0.8
        
        return min(aggregate, 1.0)


class DiagnosticsEngine:
    """Produces complete failure diagnoses from signals and classification.
    
    Main orchestration class that combines detection, classification,
    evidence aggregation, and confidence scoring to generate FailureLabels.
    
    Usage:
        engine = DiagnosticsEngine(config)
        label = engine.diagnose(signals, failure_type, confidence, explanation)
    """
    
    def __init__(self, config: Optional[DiagnosticConfig] = None):
        """Initialize diagnostics engine.
        
        Args:
            config: Diagnostic configuration
        """
        self.config = config or DEFAULT_DIAGNOSTIC_CONFIG
        self.classifier = FailureClassifier()
        self.evidence_aggregator = EvidenceAggregator()
    
    def diagnose(
        self,
        signals: List[FailureSignal],
        failure_type: FailureType,
        classification_confidence: float,
        explanation: str,
    ) -> FailureLabel:
        """Produce complete failure diagnosis.
        
        Args:
            signals: Detected failure signals
            failure_type: Classified failure type
            classification_confidence: Confidence from classification
            explanation: Human-readable explanation
            
        Returns:
            Complete FailureLabel with all diagnostic information
        """
        # Handle no failure case
        if failure_type == FailureType.NONE or not signals:
            return create_success_label(explanation)
        
        # Aggregate evidence
        evidence = self.evidence_aggregator.aggregate_evidence(signals)
        
        # Compute aggregate confidence
        aggregate_confidence = self.evidence_aggregator.compute_aggregate_confidence(
            signals,
            classification_confidence,
            require_multiple=self.config.require_multiple_signals,
        )
        
        # Check if confidence meets threshold
        if aggregate_confidence < self.config.min_confidence:
            # Low confidence - treat as partial success or no failure
            return FailureLabel(
                failure_type=FailureType.NONE,
                outcome=ExecutionOutcome.PARTIAL_SUCCESS,
                confidence=0.7,
                evidence=evidence,
                primary_signal=self._get_primary_signal_type(signals),
                explanation=f"Insufficient confidence for failure diagnosis (confidence: {aggregate_confidence:.2f})",
                severity="low",
                recoverable=True,
            )
        
        # Determine outcome
        outcome = self.classifier.determine_outcome(failure_type, aggregate_confidence)
        
        # Assign severity and recoverability
        severity = None
        recoverable = None
        
        if self.config.assign_severity:
            severity = self.classifier.assess_severity(failure_type)
        
        if self.config.analyze_recoverability:
            recoverable = self.classifier.assess_recoverability(failure_type)
        
        # Create failure label
        return FailureLabel(
            failure_type=failure_type,
            outcome=outcome,
            confidence=aggregate_confidence,
            evidence=evidence,
            primary_signal=self._get_primary_signal_type(signals),
            explanation=explanation,
            severity=severity,
            recoverable=recoverable,
        )
    
    def diagnose_from_signals(self, signals: List[FailureSignal]) -> FailureLabel:
        """Complete diagnosis pipeline from signals to label.
        
        Performs classification and diagnosis in one call.
        
        Args:
            signals: Detected failure signals
            
        Returns:
            Complete FailureLabel
        """
        # Classify signals
        failure_type, confidence, explanation = self.classifier.classify(signals)
        
        # Diagnose
        return self.diagnose(signals, failure_type, confidence, explanation)
    
    def get_alternative_diagnoses(
        self,
        signals: List[FailureSignal],
        top_k: int = 3,
    ) -> List[FailureLabel]:
        """Generate alternative failure diagnoses.
        
        Useful for ambiguous cases where multiple failure types are plausible.
        
        Args:
            signals: Detected failure signals
            top_k: Number of alternative diagnoses to generate
            
        Returns:
            List of alternative FailureLabels sorted by confidence
        """
        # Get all candidate classifications
        candidates = self.classifier.classify_all_candidates(signals)[:top_k]
        
        if not candidates:
            return [create_success_label("No failure detected")]
        
        # Generate diagnosis for each candidate
        diagnoses = []
        for failure_type, classification_conf in candidates:
            explanation = self.classifier._generate_explanation(failure_type, signals)
            diagnosis = self.diagnose(signals, failure_type, classification_conf, explanation)
            diagnoses.append(diagnosis)
        
        return diagnoses
    
    @staticmethod
    def _get_primary_signal_type(signals: List[FailureSignal]) -> Optional[str]:
        """Get the signal type of the primary (highest confidence) signal.
        
        Args:
            signals: List of signals
            
        Returns:
            Signal type string, or None if no signals
        """
        if not signals:
            return None
        primary = max(signals, key=lambda s: s.confidence)
        return primary.signal_type.value
    
    def summarize_diagnosis(self, label: FailureLabel) -> str:
        """Generate a concise summary of a failure diagnosis.
        
        Args:
            label: Failure label to summarize
            
        Returns:
            One-line summary string
        """
        if label.failure_type == FailureType.NONE:
            return f"✓ Success: {label.explanation}"
        
        severity_emoji = {
            "low": "⚠️",
            "medium": "⚠️",
            "high": "❌",
        }
        emoji = severity_emoji.get(label.severity, "⚠️")
        
        recoverable_text = " (recoverable)" if label.recoverable else ""
        
        return (
            f"{emoji} {label.failure_type.value.upper()} "
            f"(confidence: {label.confidence:.2f}, severity: {label.severity})"
            f"{recoverable_text}: {label.explanation}"
        )
    
    def create_diagnosis_report(self, label: FailureLabel) -> str:
        """Generate detailed diagnosis report.
        
        Args:
            label: Failure label
            
        Returns:
            Multi-line detailed report
        """
        lines = []
        lines.append(f"Failure Type: {label.failure_type.value}")
        lines.append(f"Outcome: {label.outcome.value}")
        lines.append(f"Confidence: {label.confidence:.2f}")
        
        if label.severity:
            lines.append(f"Severity: {label.severity}")
        
        if label.recoverable is not None:
            lines.append(f"Recoverable: {label.recoverable}")
        
        lines.append(f"\nExplanation: {label.explanation}")
        
        if label.evidence:
            lines.append(f"\nEvidence ({len(label.evidence)} signals):")
            for i, evidence in enumerate(label.evidence, 1):
                lines.append(f"  {i}. [{evidence.source}] {evidence.description}")
                lines.append(f"     Confidence: {evidence.confidence:.2f}, Value: {evidence.value}")
        
        return "\n".join(lines)
