"""
Failure Labeling Examples

Demonstrates usage of the failure labeling system for detecting and
categorizing failures in web interaction trajectories.

Examples:
1. Basic failure detection with metrics
2. Labeling a complete trajectory
3. Batch processing multiple trajectories
4. Custom diagnostic configuration
5. Alternative diagnoses for ambiguous cases
"""

import sys
from pathlib import Path
import json

# Add src to path for examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from failure_labeling import (
    FailureLabeler,
    FailureType,
    ExecutionOutcome,
    DiagnosticConfig,
    FailureDetector,
    FailureClassifier,
    DiagnosticsEngine,
    FailureSignal,
    SignalType,
)
from metric_computation import (
    StepMetrics,
    VisualMetrics,
    StateHashMetrics,
    PerformanceMetrics,
    ChangeLevel,
)


def example_1_basic_failure_detection():
    """Example 1: Basic failure detection with metrics."""
    print("=" * 70)
    print("Example 1: Basic Failure Detection")
    print("=" * 70)
    
    # Create detector
    detector = FailureDetector()
    
    # Create metrics indicating no visual change
    metrics = StepMetrics(
        step_id=0,
        visual=VisualMetrics(
            pixel_diff_score=0.002,
            ssim_score=0.98,
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
            execution_time_ms=300,
            stability_wait_ms=100,
            total_step_time_ms=400,
        ),
    )
    
    # Action log without errors
    action_log = {
        "status": "success",
        "error": None,
        "completed": True,
    }
    
    # Detect signals
    signals = detector.detect_all_signals(metrics, action_log)
    
    print(f"\nDetected {len(signals)} failure signals:")
    for signal in signals:
        print(f"  - {signal.signal_type.value}: {signal.description}")
        print(f"    Confidence: {signal.confidence:.2f}")
    
    # Classify the failure
    classifier = FailureClassifier()
    failure_type, confidence, explanation = classifier.classify(signals)
    
    print(f"\nClassification:")
    print(f"  Type: {failure_type.value}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Explanation: {explanation}")
    
    print()


def example_2_element_not_found():
    """Example 2: Element not found error."""
    print("=" * 70)
    print("Example 2: Element Not Found (Perception Error)")
    print("=" * 70)
    
    detector = FailureDetector()
    
    # Metrics showing no change
    metrics = StepMetrics(
        step_id=1,
        visual=VisualMetrics(
            pixel_diff_score=0.0,
            ssim_score=1.0,
            mse=0.0,
            change_level=ChangeLevel.NO_CHANGE,
        ),
        state_hash=StateHashMetrics(
            state_hash="xyz789",
            perceptual_hash="uvw012",
            loop_detected=False,
            state_occurrences=1,
        ),
        performance=PerformanceMetrics(
            execution_time_ms=500,
            stability_wait_ms=0,
            total_step_time_ms=500,
        ),
    )
    
    # Action log with element not found error
    action_log = {
        "status": "failed",
        "error": "Element not found: button#submit-form",
        "completed": False,
    }
    
    # Detect and diagnose
    signals = detector.detect_all_signals(metrics, action_log)
    
    diagnostics = DiagnosticsEngine()
    label = diagnostics.diagnose_from_signals(signals)
    
    print(f"\nFailure Label:")
    print(f"  Type: {label.failure_type.value}")
    print(f"  Outcome: {label.outcome.value}")
    print(f"  Confidence: {label.confidence:.2f}")
    print(f"  Severity: {label.severity}")
    print(f"  Recoverable: {label.recoverable}")
    print(f"  Explanation: {label.explanation}")
    
    print(f"\nEvidence ({len(label.evidence)} signals):")
    for evidence in label.evidence:
        print(f"  - [{evidence.source}] {evidence.description}")
        print(f"    Confidence: {evidence.confidence:.2f}")
    
    print()


def example_3_loop_detection():
    """Example 3: Loop detection."""
    print("=" * 70)
    print("Example 3: Loop Detection")
    print("=" * 70)
    
    detector = FailureDetector()
    
    # Metrics indicating loop
    metrics = StepMetrics(
        step_id=5,
        visual=VisualMetrics(
            pixel_diff_score=0.005,
            ssim_score=0.99,
            mse=0.0001,
            change_level=ChangeLevel.NO_CHANGE,
        ),
        state_hash=StateHashMetrics(
            state_hash="repeating_state",
            perceptual_hash="repeating_hash",
            loop_detected=True,  # Loop detected!
            state_occurrences=4,
        ),
        performance=PerformanceMetrics(
            execution_time_ms=400,
            stability_wait_ms=100,
            total_step_time_ms=500,
        ),
    )
    
    action_log = {"status": "success", "error": None, "completed": True}
    
    # Diagnose
    diagnostics = DiagnosticsEngine()
    signals = detector.detect_all_signals(metrics, action_log)
    label = diagnostics.diagnose_from_signals(signals)
    
    print(f"\nDiagnosis Summary:")
    summary = diagnostics.summarize_diagnosis(label)
    print(f"  {summary}")
    
    print(f"\nDetailed Report:")
    report = diagnostics.create_diagnosis_report(label)
    print(report)
    
    print()


def example_4_label_trajectory():
    """Example 4: Label a complete trajectory."""
    print("=" * 70)
    print("Example 4: Label Complete Trajectory")
    print("=" * 70)
    
    labeler = FailureLabeler()
    
    # Simulate trajectory steps
    steps_data = [
        {
            "action": {"type": "navigate", "args": {"url": "https://example.com"}},
            "status": "success",
            "completed": True,
            "url": "https://example.com",
        },
        {
            "action": {"type": "click", "args": {"selector": "button#submit"}},
            "status": "failed",
            "error": "Element not found: button#submit",
            "completed": False,
            "url": "https://example.com",
        },
        {
            "action": {"type": "click", "args": {"selector": "button.submit"}},
            "status": "success",
            "completed": True,
            "url": "https://example.com/result",
        },
    ]
    
    # Create metrics for each step
    all_metrics = [
        StepMetrics(
            step_id=0,
            visual=VisualMetrics(
                pixel_diff_score=0.3,
                ssim_score=0.7,
                mse=0.05,
                change_level=ChangeLevel.MAJOR_CHANGE
            ),
            state_hash=StateHashMetrics(
                state_hash="hash1",
                perceptual_hash="phash1",
                loop_detected=False,
                state_occurrences=1
            ),
            performance=PerformanceMetrics(
                execution_time_ms=1000,
                stability_wait_ms=200,
                total_step_time_ms=1200
            ),
        ),
        StepMetrics(
            step_id=1,
            visual=VisualMetrics(
                pixel_diff_score=0.0,
                ssim_score=1.0,
                mse=0.0,
                change_level=ChangeLevel.NO_CHANGE
            ),
            state_hash=StateHashMetrics(
                state_hash="hash1",
                perceptual_hash="phash1",
                loop_detected=False,
                state_occurrences=2
            ),
            performance=PerformanceMetrics(
                execution_time_ms=500,
                stability_wait_ms=0,
                total_step_time_ms=500
            ),
        ),
        StepMetrics(
            step_id=2,
            visual=VisualMetrics(
                pixel_diff_score=0.25,
                ssim_score=0.75,
                mse=0.04,
                change_level=ChangeLevel.MAJOR_CHANGE
            ),
            state_hash=StateHashMetrics(
                state_hash="hash2",
                perceptual_hash="phash2",
                loop_detected=False,
                state_occurrences=1
            ),
            performance=PerformanceMetrics(
                execution_time_ms=800,
                stability_wait_ms=150,
                total_step_time_ms=950
            ),
        ),
    ]
    
    # Label each step
    labeled_steps = []
    for i, step_data in enumerate(steps_data):
        previous_url = steps_data[i-1].get("url") if i > 0 else None
        current_url = step_data.get("url")
        
        labeled_step = labeler.label_step(
            step_data,
            step_number=i,
            metrics=all_metrics[i],
            previous_url=previous_url,
            current_url=current_url,
        )
        labeled_steps.append(labeled_step)
    
    # Create labeled trajectory
    trajectory = labeler._create_labeled_trajectory(
        "example_trajectory",
        "example_task",
        labeled_steps,
    )
    
    print(f"\nTrajectory Analysis:")
    analysis = labeler.analyze_trajectory(trajectory)
    print(analysis)
    
    print()


def example_5_custom_configuration():
    """Example 5: Custom diagnostic configuration."""
    print("=" * 70)
    print("Example 5: Custom Diagnostic Configuration")
    print("=" * 70)
    
    # Create custom configuration
    custom_config = DiagnosticConfig(
        min_visual_change=0.02,  # Require 2% change
        ssim_threshold=0.90,  # Lower SSIM threshold
        action_timeout_ms=5000,  # 5 second timeout
        min_confidence=0.7,  # Higher confidence threshold
        require_multiple_signals=True,  # Require multiple signals
        assign_severity=True,
        analyze_recoverability=True,
    )
    
    labeler = FailureLabeler(config=custom_config)
    
    print(f"\nCustom Configuration:")
    print(f"  Min Visual Change: {custom_config.min_visual_change}")
    print(f"  SSIM Threshold: {custom_config.ssim_threshold}")
    print(f"  Action Timeout: {custom_config.action_timeout_ms}ms")
    print(f"  Min Confidence: {custom_config.min_confidence}")
    print(f"  Require Multiple Signals: {custom_config.require_multiple_signals}")
    
    # Test with weak signal
    step_data = {
        "action": {"type": "click", "args": {}},
        "status": "success",
        "completed": True,
    }
    
    metrics = StepMetrics(
        step_id=0,
        visual=VisualMetrics(
            pixel_diff_score=0.015,
            ssim_score=0.92,
            mse=0.001,
            change_level=ChangeLevel.MINOR_CHANGE
        ),
        state_hash=StateHashMetrics(
            state_hash="hash",
            perceptual_hash="phash",
            loop_detected=False,
            state_occurrences=1
        ),
        performance=PerformanceMetrics(
            execution_time_ms=300,
            stability_wait_ms=50,
            total_step_time_ms=350
        ),
    )
    
    labeled_step = labeler.label_step(step_data, 0, metrics)
    
    print(f"\nLabeled with Custom Config:")
    print(f"  Outcome: {labeled_step.failure_label.outcome.value}")
    print(f"  Explanation: {labeled_step.failure_label.explanation}")
    
    print()


def example_6_alternative_diagnoses():
    """Example 6: Alternative diagnoses for ambiguous cases."""
    print("=" * 70)
    print("Example 6: Alternative Diagnoses")
    print("=" * 70)
    
    diagnostics = DiagnosticsEngine()
    detector = FailureDetector()
    
    # Ambiguous case: timeout + no change
    metrics = StepMetrics(
        step_id=0,
        visual=VisualMetrics(
            pixel_diff_score=0.003,
            ssim_score=0.98,
            mse=0.0001,
            change_level=ChangeLevel.NO_CHANGE
        ),
        state_hash=StateHashMetrics(
            state_hash="hash",
            perceptual_hash="phash",
            loop_detected=False,
            state_occurrences=1
        ),
        performance=PerformanceMetrics(
            execution_time_ms=35000,
            stability_wait_ms=1000,
            total_step_time_ms=36000
        ),  # Timeout!
    )
    
    action_log = {"status": "success", "error": None, "completed": True}
    
    signals = detector.detect_all_signals(metrics, action_log)
    
    # Get alternative diagnoses
    alternatives = diagnostics.get_alternative_diagnoses(signals, top_k=3)
    
    print(f"\nDetected {len(signals)} signals:")
    for signal in signals:
        print(f"  - {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
    
    print(f"\nAlternative Diagnoses:")
    for i, label in enumerate(alternatives, 1):
        print(f"\n{i}. {label.failure_type.value}")
        print(f"   Confidence: {label.confidence:.2f}")
        print(f"   Outcome: {label.outcome.value}")
        print(f"   Explanation: {label.explanation}")
    
    print()


def run_all_examples():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("FAILURE LABELING EXAMPLES")
    print("=" * 70 + "\n")
    
    example_1_basic_failure_detection()
    example_2_element_not_found()
    example_3_loop_detection()
    example_4_label_trajectory()
    example_5_custom_configuration()
    example_6_alternative_diagnoses()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
