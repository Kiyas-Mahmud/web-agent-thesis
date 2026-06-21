"""
Failure Labeling Validation Script

Comprehensive validation of the failure labeling system including:
- Schema validation
- Signal detection
- Classification rules
- Diagnostics engine
- End-to-end labeling

Run: python scripts/validate_failure_labeling.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from failure_labeling.failure_schema import (
    FailureType,
    ExecutionOutcome,
    FailureEvidence,
    FailureLabel,
    LabeledStep,
    LabeledTrajectory,
    DiagnosticConfig,
    create_failure_label,
    create_success_label,
)
from failure_labeling.failure_detector import (
    FailureDetector,
    FailureSignal,
    SignalType,
)
from failure_labeling.failure_classifier import (
    FailureClassifier,
    ClassificationRule,
)
from failure_labeling.diagnostics_engine import (
    DiagnosticsEngine,
    EvidenceAggregator,
)
from failure_labeling.failure_labeler import (
    FailureLabeler,
)
from metric_computation.metric_schema import (
    StepMetrics,
    VisualMetrics,
    StateHashMetrics,
    PerformanceMetrics,
    ChangeLevel,
)


class ValidationTest:
    """Base class for validation tests."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
    
    def run(self) -> bool:
        """Run the test. Override in subclasses."""
        raise NotImplementedError
    
    def execute(self) -> bool:
        """Execute test with error handling."""
        try:
            self.passed = self.run()
            return self.passed
        except Exception as e:
            self.error = str(e)
            self.passed = False
            return False


# ============================================================================
# Schema Validation Tests
# ============================================================================

class TestFailureTypeEnum(ValidationTest):
    """Test FailureType enum has all 9 categories."""
    
    def run(self) -> bool:
        expected_types = {
            "perception_error",
            "action_mismatch",
            "state_no_change",
            "loop_detected",
            "goal_misalignment",
            "tool_failure",
            "ui_variation",
            "reasoning_error",
            "none",
        }
        actual_types = {ft.value for ft in FailureType}
        assert actual_types == expected_types, f"Missing types: {expected_types - actual_types}"
        return True


class TestFailureLabel(ValidationTest):
    """Test FailureLabel creation and validation."""
    
    def run(self) -> bool:
        label = create_failure_label(
            FailureType.PERCEPTION_ERROR,
            ExecutionOutcome.FAILURE,
            0.9,
            "Element not found",
        )
        assert label.failure_type == FailureType.PERCEPTION_ERROR
        assert label.confidence == 0.9
        assert label.outcome == ExecutionOutcome.FAILURE
        return True


class TestSuccessLabel(ValidationTest):
    """Test success label creation."""
    
    def run(self) -> bool:
        label = create_success_label()
        assert label.failure_type == FailureType.NONE
        assert label.outcome == ExecutionOutcome.SUCCESS
        assert label.confidence == 1.0
        assert label.severity == "low"
        assert label.recoverable is True
        return True


class TestDiagnosticConfig(ValidationTest):
    """Test diagnostic configuration."""
    
    def run(self) -> bool:
        config = DiagnosticConfig(
            min_visual_change=0.02,
            ssim_threshold=0.9,
            min_confidence=0.6,
        )
        assert config.min_visual_change == 0.02
        assert config.ssim_threshold == 0.9
        assert config.min_confidence == 0.6
        return True


class TestLabeledTrajectory(ValidationTest):
    """Test labeled trajectory creation."""
    
    def run(self) -> bool:
        step = LabeledStep(
            step_number=0,
            action_type="click",
            action_args={"selector": "button"},
            failure_label=create_success_label(),
        )
        
        trajectory = LabeledTrajectory(
            trajectory_id="test_traj_001",
            steps=[step],
            overall_outcome=ExecutionOutcome.SUCCESS,
            failure_summary={"none": 1},
            total_steps=1,
            failed_steps=0,
            success_rate=1.0,
        )
        
        assert trajectory.total_steps == 1
        assert trajectory.success_rate == 1.0
        return True


# ============================================================================
# Signal Detection Tests
# ============================================================================

class TestVisualSignalDetection(ValidationTest):
    """Test detection of visual change signals."""
    
    def run(self) -> bool:
        detector = FailureDetector()
        
        # Create metrics with no visual change
        visual_metrics = VisualMetrics(
            pixel_diff_score=0.005,
            ssim_score=0.99,
            mse=0.0001,
            change_level=ChangeLevel.NO_CHANGE,
        )
        
        signals = detector._detect_visual_signals(visual_metrics)
        
        # Should detect no change
        assert len(signals) > 0
        assert any(s.signal_type == SignalType.NO_VISUAL_CHANGE for s in signals)
        
        # Check confidence
        no_change_signal = next(s for s in signals if s.signal_type == SignalType.NO_VISUAL_CHANGE)
        assert 0.0 <= no_change_signal.confidence <= 1.0
        
        return True


class TestLoopDetection(ValidationTest):
    """Test loop detection signal."""
    
    def run(self) -> bool:
        detector = FailureDetector()
        
        # Create metrics with loop detected
        state_metrics = StateHashMetrics(
            state_hash="abc123",
            perceptual_hash="def456",
            loop_detected=True,
            state_occurrences=3,
        )
        
        signals = detector._detect_state_signals(state_metrics)
        
        # Should detect loop
        assert len(signals) > 0
        loop_signals = [s for s in signals if s.signal_type == SignalType.LOOP_DETECTED]
        assert len(loop_signals) > 0
        assert loop_signals[0].confidence >= 0.8  # High confidence
        
        return True


class TestExceptionDetection(ValidationTest):
    """Test exception signal detection."""
    
    def run(self) -> bool:
        detector = FailureDetector()
        
        # Action log with element not found error
        action_log = {
            "status": "failed",
            "error": "Element not found: button#submit",
            "completed": False,
        }
        
        signals = detector._detect_exception_signals(action_log)
        
        # Should detect multiple signals
        assert len(signals) > 0
        signal_types = {s.signal_type for s in signals}
        assert SignalType.ELEMENT_NOT_FOUND in signal_types
        
        return True


class TestTimeoutDetection(ValidationTest):
    """Test timeout signal detection."""
    
    def run(self) -> bool:
        detector = FailureDetector(DiagnosticConfig(action_timeout_ms=1000))
        
        # Performance metrics with timeout
        perf_metrics = PerformanceMetrics(
            execution_time_ms=5000,
            stability_wait_ms=0,
            total_step_time_ms=5000,
        )
        
        signals = detector._detect_performance_signals(perf_metrics)
        
        # Should detect timeout
        assert len(signals) > 0
        timeout_signals = [s for s in signals if s.signal_type == SignalType.ACTION_TIMEOUT]
        assert len(timeout_signals) > 0
        
        return True


class TestUIVariationDetection(ValidationTest):
    """Test UI variation signal detection."""
    
    def run(self) -> bool:
        detector = FailureDetector()
        
        # URLs indicating redirect
        previous_url = "https://example.com/page1"
        current_url = "https://different-site.com/page2"
        
        signals = detector._detect_ui_signals(previous_url, current_url)
        
        # Should detect redirect
        assert len(signals) > 0
        redirect_signals = [s for s in signals if s.signal_type == SignalType.UNEXPECTED_REDIRECT]
        assert len(redirect_signals) > 0
        
        return True


# ============================================================================
# Classification Tests
# ============================================================================

class TestClassificationRules(ValidationTest):
    """Test classification rule creation."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        # Should have rules for all failure types
        rule_types = {rule.failure_type for rule in classifier.rules}
        
        # Should have at least one rule for major failure types
        assert FailureType.PERCEPTION_ERROR in rule_types
        assert FailureType.LOOP_DETECTED in rule_types
        assert FailureType.TOOL_FAILURE in rule_types
        
        return True


class TestPerceptionErrorClassification(ValidationTest):
    """Test classification of perception errors."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        # Create signal for element not found
        signals = [
            FailureSignal(
                signal_type=SignalType.ELEMENT_NOT_FOUND,
                confidence=0.9,
                source="action_log",
                value="Element not found",
                description="Element not found: button#submit"
            )
        ]
        
        failure_type, confidence, explanation = classifier.classify(signals)
        
        assert failure_type == FailureType.PERCEPTION_ERROR
        assert confidence > 0.6
        assert "element not found" in explanation.lower() or "perception" in explanation.lower()
        
        return True


class TestLoopDetectedClassification(ValidationTest):
    """Test classification of loop failures."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.LOOP_DETECTED,
                confidence=0.9,
                source="state_hash",
                value=True,
                description="Loop detected"
            )
        ]
        
        failure_type, confidence, explanation = classifier.classify(signals)
        
        assert failure_type == FailureType.LOOP_DETECTED
        assert confidence > 0.7
        
        return True


class TestStateNoChangeClassification(ValidationTest):
    """Test classification of state no change."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.NO_VISUAL_CHANGE,
                confidence=0.85,
                source="visual_metrics",
                value=0.002,
                description="No visual change detected"
            )
        ]
        
        failure_type, confidence, explanation = classifier.classify(signals)
        
        assert failure_type == FailureType.STATE_NO_CHANGE
        assert confidence > 0.5
        
        return True


class TestToolFailureClassification(ValidationTest):
    """Test classification of tool failures."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.BROWSER_EXCEPTION,
                confidence=0.8,
                source="action_log",
                value="TimeoutError",
                description="Browser exception: TimeoutError"
            )
        ]
        
        failure_type, confidence, explanation = classifier.classify(signals)
        
        assert failure_type == FailureType.TOOL_FAILURE
        assert confidence > 0.5
        
        return True


class TestNoFailureClassification(ValidationTest):
    """Test classification when no failure."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        signals = []  # No signals
        
        failure_type, confidence, explanation = classifier.classify(signals)
        
        assert failure_type == FailureType.NONE
        assert confidence == 1.0
        
        return True


class TestOutcomeDetermination(ValidationTest):
    """Test execution outcome determination."""
    
    def run(self) -> bool:
        classifier = FailureClassifier()
        
        # High confidence failure
        outcome = classifier.determine_outcome(FailureType.PERCEPTION_ERROR, 0.9)
        assert outcome == ExecutionOutcome.FAILURE
        
        # Medium confidence
        outcome = classifier.determine_outcome(FailureType.STATE_NO_CHANGE, 0.6)
        assert outcome == ExecutionOutcome.PARTIAL_SUCCESS
        
        # Success
        outcome = classifier.determine_outcome(FailureType.NONE, 1.0)
        assert outcome == ExecutionOutcome.SUCCESS
        
        return True


# ============================================================================
# Diagnostics Engine Tests
# ============================================================================

class TestEvidenceAggregation(ValidationTest):
    """Test evidence aggregation from signals."""
    
    def run(self) -> bool:
        aggregator = EvidenceAggregator()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.NO_VISUAL_CHANGE,
                confidence=0.8,
                source="visual_metrics",
                value=0.003,
                description="No change"
            ),
            FailureSignal(
                signal_type=SignalType.REPEATED_STATE,
                confidence=0.6,
                source="state_hash",
                value=2,
                description="State repeated"
            ),
        ]
        
        evidence = aggregator.aggregate_evidence(signals)
        
        assert len(evidence) == 2
        assert all(isinstance(e, FailureEvidence) for e in evidence)
        assert evidence[0].confidence == 0.8
        
        return True


class TestConfidenceComputation(ValidationTest):
    """Test aggregate confidence computation."""
    
    def run(self) -> bool:
        aggregator = EvidenceAggregator()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.ELEMENT_NOT_FOUND,
                confidence=0.9,
                source="action_log",
                value="error",
                description="Element not found"
            ),
            FailureSignal(
                signal_type=SignalType.NO_VISUAL_CHANGE,
                confidence=0.7,
                source="visual_metrics",
                value=0.001,
                description="No change"
            ),
        ]
        
        confidence = aggregator.compute_aggregate_confidence(
            signals,
            classification_confidence=0.85,
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high with strong signals
        
        return True


class TestDiagnosisGeneration(ValidationTest):
    """Test complete diagnosis generation."""
    
    def run(self) -> bool:
        engine = DiagnosticsEngine()
        
        signals = [
            FailureSignal(
                signal_type=SignalType.LOOP_DETECTED,
                confidence=0.9,
                source="state_hash",
                value=True,
                description="Loop detected"
            )
        ]
        
        label = engine.diagnose_from_signals(signals)
        
        assert isinstance(label, FailureLabel)
        assert label.failure_type == FailureType.LOOP_DETECTED
        assert label.confidence > 0.7
        assert len(label.evidence) > 0
        assert label.severity in ["low", "medium", "high"]
        assert label.recoverable is not None
        
        return True


class TestMinConfidenceThreshold(ValidationTest):
    """Test minimum confidence threshold filtering."""
    
    def run(self) -> bool:
        config = DiagnosticConfig(min_confidence=0.8)
        engine = DiagnosticsEngine(config)
        
        # Weak signals below threshold
        signals = [
            FailureSignal(
                signal_type=SignalType.MINIMAL_VISUAL_CHANGE,
                confidence=0.4,
                source="visual_metrics",
                value=0.015,
                description="Minimal change"
            )
        ]
        
        label = engine.diagnose_from_signals(signals)
        
        # Should not label as failure due to low confidence
        assert label.failure_type == FailureType.NONE or label.outcome == ExecutionOutcome.PARTIAL_SUCCESS
        
        return True


# ============================================================================
# Integration Tests
# ============================================================================

class TestFailureLabelerInitialization(ValidationTest):
    """Test FailureLabeler initialization."""
    
    def run(self) -> bool:
        labeler = FailureLabeler()
        
        assert labeler.config is not None
        assert labeler.detector is not None
        assert labeler.classifier is not None
        assert labeler.diagnostics is not None
        
        return True


class TestStepLabeling(ValidationTest):
    """Test labeling of a single step."""
    
    def run(self) -> bool:
        labeler = FailureLabeler()
        
        # Create step data with failure
        step_data = {
            "action": {"type": "click", "args": {"selector": "button"}},
            "status": "failed",
            "error": "Element not found: button",
            "completed": False,
        }
        
        # Create metrics
        metrics = StepMetrics(
            step_id=0,
            visual=VisualMetrics(
                pixel_diff_score=0.001,
                ssim_score=0.99,
                mse=0.0001,
                change_level=ChangeLevel.NO_CHANGE,
            ),
            state_hash=StateHashMetrics(
                state_hash="abc123",
                perceptual_hash="def456",
                loop_detected=False,
                state_occurrences=1,
            ),
            performance=PerformanceMetrics(
                execution_time_ms=500,
                stability_wait_ms=100,
                total_step_time_ms=600,
            ),
        )
        
        labeled_step = labeler.label_step(step_data, 0, metrics)
        
        assert isinstance(labeled_step, LabeledStep)
        assert labeled_step.step_number == 0
        assert labeled_step.action_type == "click"
        assert labeled_step.failure_label.failure_type == FailureType.PERCEPTION_ERROR
        
        return True


class TestSuccessfulStepLabeling(ValidationTest):
    """Test labeling of successful step."""
    
    def run(self) -> bool:
        labeler = FailureLabeler()
        
        step_data = {
            "action": {"type": "click", "args": {"selector": "button"}},
            "status": "success",
            "completed": True,
        }
        
        metrics = StepMetrics(
            step_id=0,
            visual=VisualMetrics(
                pixel_diff_score=0.15,
                ssim_score=0.85,
                mse=0.02,
                change_level=ChangeLevel.MAJOR_CHANGE,
            ),
            state_hash=StateHashMetrics(
                state_hash="xyz789",
                perceptual_hash="uvw012",
                loop_detected=False,
                state_occurrences=1,
            ),
            performance=PerformanceMetrics(
                execution_time_ms=300,
                stability_wait_ms=50,
                total_step_time_ms=350,
            ),
        )
        
        labeled_step = labeler.label_step(step_data, 0, metrics)
        
        # Should be success or partial success
        assert labeled_step.failure_label.outcome in [ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS]
        
        return True


class TestTrajectoryCreation(ValidationTest):
    """Test labeled trajectory creation."""
    
    def run(self) -> bool:
        labeler = FailureLabeler()
        
        steps = [
            LabeledStep(
                step_number=0,
                action_type="click",
                action_args={},
                failure_label=create_success_label(),
            ),
            LabeledStep(
                step_number=1,
                action_type="type",
                action_args={},
                failure_label=create_failure_label(
                    FailureType.PERCEPTION_ERROR,
                    ExecutionOutcome.FAILURE,
                    0.9,
                    "Element not found"
                ),
            ),
        ]
        
        trajectory = labeler._create_labeled_trajectory("test_001", "task_001", steps)
        
        assert trajectory.total_steps == 2
        assert trajectory.failed_steps == 1
        assert trajectory.success_rate == 0.5
        assert trajectory.first_failure_step == 1
        assert "perception_error" in trajectory.failure_summary
        
        return True


# ============================================================================
# Run All Tests
# ============================================================================

def run_validation():
    """Run all validation tests."""
    
    test_categories = {
        "Schema Validation": [
            TestFailureTypeEnum("FailureType enum completeness"),
            TestFailureLabel("FailureLabel creation"),
            TestSuccessLabel("Success label creation"),
            TestDiagnosticConfig("Diagnostic configuration"),
            TestLabeledTrajectory("Labeled trajectory creation"),
        ],
        "Signal Detection": [
            TestVisualSignalDetection("Visual signal detection"),
            TestLoopDetection("Loop detection signal"),
            TestExceptionDetection("Exception signal detection"),
            TestTimeoutDetection("Timeout signal detection"),
            TestUIVariationDetection("UI variation detection"),
        ],
        "Classification": [
            TestClassificationRules("Classification rules"),
            TestPerceptionErrorClassification("Perception error classification"),
            TestLoopDetectedClassification("Loop detected classification"),
            TestStateNoChangeClassification("State no change classification"),
            TestToolFailureClassification("Tool failure classification"),
            TestNoFailureClassification("No failure classification"),
            TestOutcomeDetermination("Outcome determination"),
        ],
        "Diagnostics": [
            TestEvidenceAggregation("Evidence aggregation"),
            TestConfidenceComputation("Confidence computation"),
            TestDiagnosisGeneration("Diagnosis generation"),
            TestMinConfidenceThreshold("Min confidence threshold"),
        ],
        "Integration": [
            TestFailureLabelerInitialization("FailureLabeler initialization"),
            TestStepLabeling("Step labeling with failure"),
            TestSuccessfulStepLabeling("Successful step labeling"),
            TestTrajectoryCreation("Trajectory creation"),
        ],
    }
    
    print("=" * 70)
    print("FAILURE LABELING VALIDATION")
    print("=" * 70)
    
    total_tests = sum(len(tests) for tests in test_categories.values())
    passed_tests = 0
    failed_tests = 0
    
    for category, tests in test_categories.items():
        print(f"\n{category}")
        print("-" * 70)
        
        for test in tests:
            result = test.execute()
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test.name}")
            
            if not result:
                if test.error:
                    print(f"  Error: {test.error}")
                failed_tests += 1
            else:
                passed_tests += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests > 0:
        print(f"WARNING: {failed_tests} tests failed")
        return False
    else:
        print("SUCCESS: All tests passed!")
        return True


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
