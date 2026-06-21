"""
Validation Script for Task-06: Reflection Annotation

Tests reflection annotation system:
- Schema validation
- Confidence estimation
- Reflection text generation
- Memory signal detection
- End-to-end annotation
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from reflection_annotation.reflection_schema import (
    ReflectionAnnotation,
    ReflectionConfig,
    MemoryType,
    ReasoningType,
    UncertaintySource,
    IntrospectionMetadata,
    create_reflection_annotation,
)
from reflection_annotation.confidence_estimator import (
    ConfidenceEstimator,
    ConfidenceFactors,
)
from reflection_annotation.reflection_generator import ReflectionGenerator
from reflection_annotation.memory_signals import MemorySignalDetector
from reflection_annotation.reflection_annotator import ReflectionAnnotator


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(name: str, passed: bool, message: str = "") -> None:
    """Print test result."""
    status = f"{Colors.GREEN}✓{Colors.RESET}" if passed else f"{Colors.RED}✗{Colors.RESET}"
    print(f"{status} {name}", end="")
    if message:
        print(f": {message}")
    else:
        print()


def print_section(name: str) -> None:
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{name}{Colors.RESET}")


def test_schema_validation() -> int:
    """Test schema models."""
    print_section("Testing Schema Validation")
    passed = 0
    total = 0
    
    # Test 1: Create reflection annotation
    total += 1
    try:
        annotation = create_reflection_annotation(
            step_id=0,
            confidence_before=0.8,
            confidence_after=0.9,
            reflection_text="Successfully clicked button.",
            memory_update=False,
            memory_type=MemoryType.NONE,
        )
        assert annotation.step_id == 0
        assert annotation.agent_confidence_before == 0.8
        assert annotation.agent_confidence_after == 0.9
        assert annotation.confidence_delta == 0.1
        print_test("Create basic annotation", True)
        passed += 1
    except Exception as e:
        print_test("Create basic annotation", False, str(e))
    
    # Test 2: Annotation with metadata
    total += 1
    try:
        metadata = IntrospectionMetadata(
            reasoning_type=ReasoningType.EXECUTION,
            uncertainty_source=UncertaintySource.NONE,
            learning_signal="weak",
        )
        annotation = create_reflection_annotation(
            step_id=1,
            confidence_before=0.7,
            confidence_after=0.85,
            reflection_text="Action succeeded.",
            memory_update=True,
            memory_type=MemoryType.SUCCESS,
        )
        assert annotation.introspection_metadata.reasoning_type == ReasoningType.EXECUTION
        print_test("Annotation with metadata", True)
        passed += 1
    except Exception as e:
        print_test("Annotation with metadata", False, str(e))
    
    # Test 3: Config validation
    total += 1
    try:
        config = ReflectionConfig(
            base_confidence=0.75,
            confidence_threshold=0.7,
        )
        assert config.base_confidence == 0.75
        assert config.confidence_threshold == 0.7
        print_test("Config validation", True)
        passed += 1
    except Exception as e:
        print_test("Config validation", False, str(e))
    
    # Test 4: Memory type enum
    total += 1
    try:
        assert MemoryType.SUCCESS.value == "success"
        assert MemoryType.FAILURE.value == "failure"
        assert MemoryType.RECOVERY.value == "recovery"
        print_test("Memory type enum", True)
        passed += 1
    except Exception as e:
        print_test("Memory type enum", False, str(e))
    
    # Test 5: Reasoning type enum
    total += 1
    try:
        assert ReasoningType.DIAGNOSIS.value == "diagnosis"
        assert ReasoningType.RECOVERY.value == "recovery"
        print_test("Reasoning type enum", True)
        passed += 1
    except Exception as e:
        print_test("Reasoning type enum", False, str(e))
    
    # Test 6: Uncertainty source enum
    total += 1
    try:
        assert UncertaintySource.ELEMENT_DETECTION.value == "element_detection"
        assert UncertaintySource.PAGE_STATE.value == "page_state"
        print_test("Uncertainty source enum", True)
        passed += 1
    except Exception as e:
        print_test("Uncertainty source enum", False, str(e))
    
    # Test 7: Confidence delta calculation
    total += 1
    try:
        annotation = create_reflection_annotation(
            step_id=2,
            confidence_before=0.9,
            confidence_after=0.5,
            reflection_text="Test reflection",
        )
        assert abs(annotation.confidence_delta - (-0.4)) < 0.01
        print_test("Confidence delta calculation", True)
        passed += 1
    except Exception as e:
        print_test("Confidence delta calculation", False, str(e))
    
    return passed, total


def test_confidence_estimation() -> int:
    """Test confidence estimation."""
    print_section("Testing Confidence Estimation")
    passed = 0
    total = 0
    
    estimator = ConfidenceEstimator()
    
    # Test 1: High confidence scenario
    total += 1
    try:
        factors = ConfidenceFactors(
            element_found=True,
            element_visibility=1.0,
            selector_confidence=0.95,
            page_loaded=True,
            page_stable=True,
            visual_change_detected=True,
            state_change_detected=True,
        )
        confidence = estimator.estimate_before_action(factors)
        assert confidence >= 0.7, f"Expected >= 0.7, got {confidence}"
        print_test("High confidence before action", True)
        passed += 1
    except Exception as e:
        print_test("High confidence before action", False, str(e))
    
    # Test 2: Low confidence scenario (element not found)
    total += 1
    try:
        factors = ConfidenceFactors(
            element_found=False,
            element_visibility=0.0,
            selector_confidence=0.1,
        )
        confidence = estimator.estimate_before_action(factors)
        assert confidence <= 0.6, f"Expected <= 0.6, got {confidence}"
        print_test("Low confidence (element not found)", True)
        passed += 1
    except Exception as e:
        print_test("Low confidence (element not found)", False, str(e))
    
    # Test 3: After action with success
    total += 1
    try:
        factors = ConfidenceFactors(
            visual_change_detected=True,
            state_change_detected=True,
            failure_type=None,
        )
        confidence = estimator.estimate_after_action(factors, confidence_before=0.8)
        assert confidence >= 0.8, f"Expected >= 0.8, got {confidence}"
        print_test("High confidence after success", True)
        passed += 1
    except Exception as e:
        print_test("High confidence after success", False, str(e))
    
    # Test 4: After action with failure
    total += 1
    try:
        factors = ConfidenceFactors(
            visual_change_detected=False,
            state_change_detected=False,
            failure_type="element_not_found",
            failure_severity=0.8,
        )
        confidence = estimator.estimate_after_action(factors, confidence_before=0.8)
        assert confidence <= 0.6, f"Expected <= 0.6, got {confidence}"
        print_test("Low confidence after failure", True)
        passed += 1
    except Exception as e:
        print_test("Low confidence after failure", False, str(e))
    
    # Test 5: Recovery success boost
    total += 1
    try:
        factors = ConfidenceFactors(
            recovery_attempted=True,
            recovery_success=True,
            recovery_strategy="alternative_selector",
            visual_change_detected=True,  # Add visual change
            state_change_detected=False,
        )
        confidence = estimator.estimate_after_action(factors, confidence_before=0.7)
        assert confidence >= 0.75, f"Expected >= 0.75, got {confidence}"
        print_test("Recovery success boost", True)
        passed += 1
    except Exception as e:
        print_test("Recovery success boost", False, str(e))
    
    # Test 6: Action history tracking
    total += 1
    try:
        estimator.update_history(True)
        estimator.update_history(True)
        estimator.update_history(False)
        success_rate = estimator.get_recent_success_rate(window=3)
        assert abs(success_rate - 0.667) < 0.01, f"Expected ~0.667, got {success_rate}"
        print_test("Action history tracking", True)
        passed += 1
    except Exception as e:
        print_test("Action history tracking", False, str(e))
    
    # Test 7: Page complexity penalty
    total += 1
    try:
        factors_simple = ConfidenceFactors(page_complexity=0.2)
        factors_complex = ConfidenceFactors(page_complexity=0.9)
        conf_simple = estimator.estimate_before_action(factors_simple)
        conf_complex = estimator.estimate_before_action(factors_complex)
        assert conf_simple > conf_complex, "Simple page should have higher confidence"
        print_test("Page complexity penalty", True)
        passed += 1
    except Exception as e:
        print_test("Page complexity penalty", False, str(e))
    
    return passed, total


def test_reflection_generation() -> int:
    """Test reflection text generation."""
    print_section("Testing Reflection Generation")
    passed = 0
    total = 0
    
    generator = ReflectionGenerator()
    
    # Test 1: Success reflection
    total += 1
    try:
        action = {"type": "click", "target": "button#submit"}
        outcome = {"success": True, "state_changed": True}
        metrics = {"visual": {"pixel_diff": 0.15}}
        
        reflection = generator.generate_reflection(action, outcome, metrics=metrics)
        assert len(reflection) > 0, "Reflection should not be empty"
        assert "click" in reflection.lower(), "Should mention action type"
        print_test("Success reflection", True, f"'{reflection[:50]}...'")
        passed += 1
    except Exception as e:
        print_test("Success reflection", False, str(e))
    
    # Test 2: Failure reflection
    total += 1
    try:
        action = {"type": "type", "target": "input#email"}
        outcome = {"success": False}
        failure_info = {
            "failure_type": "element_not_found",
            "primary_signal": "no_visual_change",
        }
        
        reflection = generator.generate_reflection(action, outcome, failure_info=failure_info)
        assert "fail" in reflection.lower(), "Should mention failure"
        assert "element_not_found" in reflection.lower() or "not found" in reflection.lower()
        print_test("Failure reflection", True, f"'{reflection[:50]}...'")
        passed += 1
    except Exception as e:
        print_test("Failure reflection", False, str(e))
    
    # Test 3: Recovery reflection
    total += 1
    try:
        action = {"type": "click", "target": "button"}
        outcome = {"success": False}
        recovery_info = {
            "attempted": True,
            "success": True,
            "strategy": "alternative_selector",
        }
        
        reflection = generator.generate_reflection(action, outcome, recovery_info=recovery_info)
        assert "recovery" in reflection.lower() or "alternative" in reflection.lower()
        print_test("Recovery reflection", True, f"'{reflection[:50]}...'")
        passed += 1
    except Exception as e:
        print_test("Recovery reflection", False, str(e))
    
    # Test 4: Timeout reflection
    total += 1
    try:
        action = {"type": "navigate", "url": "https://example.com"}
        outcome = {"timeout": True, "timeout_duration": 30}
        
        reflection = generator.generate_reflection(action, outcome)
        assert "timeout" in reflection.lower() or "timed out" in reflection.lower()
        print_test("Timeout reflection", True, f"'{reflection[:50]}...'")
        passed += 1
    except Exception as e:
        print_test("Timeout reflection", False, str(e))
    
    # Test 5: Loop detection reflection
    total += 1
    try:
        action = {"type": "click", "target": "button"}
        outcome = {"loop_detected": True, "loop_info": {"size": 3}}
        
        reflection = generator.generate_reflection(action, outcome)
        assert "loop" in reflection.lower(), "Should mention loop"
        print_test("Loop detection reflection", True, f"'{reflection[:50]}...'")
        passed += 1
    except Exception as e:
        print_test("Loop detection reflection", False, str(e))
    
    # Test 6: Reflection length limit
    total += 1
    try:
        config = ReflectionConfig(max_reflection_length=50)
        generator = ReflectionGenerator(config)
        action = {"type": "click", "target": "button"}
        outcome = {"success": True}
        
        reflection = generator.generate_reflection(action, outcome)
        assert len(reflection) <= 50, f"Should be <= 50 chars, got {len(reflection)}"
        print_test("Reflection length limit", True)
        passed += 1
    except Exception as e:
        print_test("Reflection length limit", False, str(e))
    
    return passed, total


def test_memory_signals() -> int:
    """Test memory signal detection."""
    print_section("Testing Memory Signal Detection")
    passed = 0
    total = 0
    
    detector = MemorySignalDetector()
    
    # Test 1: Novel failure detection
    total += 1
    try:
        failure_info = {
            "failure_type": "element_not_interactable",
            "confidence": 0.85,
        }
        should_update, memory_type = detector.detect_memory_signal(
            confidence_before=0.8,
            confidence_after=0.4,
            failure_info=failure_info,
        )
        assert should_update, "Should flag novel failure"
        assert memory_type == MemoryType.FAILURE, f"Expected FAILURE, got {memory_type}"
        print_test("Novel failure detection", True)
        passed += 1
    except Exception as e:
        print_test("Novel failure detection", False, str(e))
    
    # Test 2: Successful recovery detection
    total += 1
    try:
        recovery_info = {
            "attempted": True,
            "success": True,
            "strategy": "wait_and_retry",
        }
        should_update, memory_type = detector.detect_memory_signal(
            confidence_before=0.5,
            confidence_after=0.85,
            recovery_info=recovery_info,
        )
        assert should_update, "Should flag successful recovery"
        assert memory_type == MemoryType.RECOVERY, f"Expected RECOVERY, got {memory_type}"
        print_test("Successful recovery detection", True)
        passed += 1
    except Exception as e:
        print_test("Successful recovery detection", False, str(e))
    
    # Test 3: High uncertainty detection
    total += 1
    try:
        should_update, memory_type = detector.detect_memory_signal(
            confidence_before=0.3,
            confidence_after=0.35,
        )
        assert should_update, "Should flag high uncertainty"
        assert memory_type == MemoryType.INSIGHT, f"Expected INSIGHT, got {memory_type}"
        print_test("High uncertainty detection", True)
        passed += 1
    except Exception as e:
        print_test("High uncertainty detection", False, str(e))
    
    # Test 4: Notable success detection
    total += 1
    try:
        outcome = {"success": True}
        should_update, memory_type = detector.detect_memory_signal(
            confidence_before=0.7,
            confidence_after=0.95,  # High confidence success
            outcome=outcome,
        )
        assert should_update, "Should flag notable success"
        assert memory_type == MemoryType.SUCCESS, f"Expected SUCCESS, got {memory_type}"
        print_test("Notable success detection", True)
        passed += 1
    except Exception as e:
        print_test("Notable success detection", False, str(e))
    
    # Test 5: No memory signal for routine success
    total += 1
    try:
        outcome = {"success": True}
        should_update, memory_type = detector.detect_memory_signal(
            confidence_before=0.8,
            confidence_after=0.85,
            outcome=outcome,
        )
        assert not should_update, "Should not flag routine success"
        assert memory_type == MemoryType.NONE, f"Expected NONE, got {memory_type}"
        print_test("No signal for routine success", True)
        passed += 1
    except Exception as e:
        print_test("No signal for routine success", False, str(e))
    
    # Test 6: Statistics tracking
    total += 1
    try:
        stats = detector.get_statistics()
        assert "total_steps" in stats
        assert "memory_signals" in stats
        assert "memory_rate" in stats
        print_test("Statistics tracking", True)
        passed += 1
    except Exception as e:
        print_test("Statistics tracking", False, str(e))
    
    return passed, total


def test_full_annotation() -> int:
    """Test end-to-end annotation."""
    print_section("Testing Full Annotation Pipeline")
    passed = 0
    total = 0
    
    annotator = ReflectionAnnotator()
    
    # Test 1: Annotate single step (success)
    total += 1
    try:
        action = {"type": "click", "target": "button#submit", "element_found": True}
        outcome = {"success": True, "page_loaded": True, "state_changed": True}
        metrics = {
            "visual": {"pixel_diff": 0.2},
            "state_hash": {"changed": True},
        }
        
        annotation = annotator.annotate_step(0, action, outcome, metrics=metrics)
        assert annotation.step_id == 0
        assert annotation.agent_confidence_before >= 0
        assert annotation.agent_confidence_after >= 0
        assert len(annotation.reflection_text) > 0
        print_test("Annotate success step", True)
        passed += 1
    except Exception as e:
        print_test("Annotate success step", False, str(e))
    
    # Test 2: Annotate step with failure
    total += 1
    try:
        action = {"type": "type", "target": "input#email"}
        outcome = {"success": False}
        failure_info = {
            "failure_type": "element_not_found",
            "severity": 0.8,
            "confidence": 0.9,
        }
        
        annotation = annotator.annotate_step(1, action, outcome, failure_info=failure_info)
        assert annotation.agent_confidence_after < annotation.agent_confidence_before
        assert "fail" in annotation.reflection_text.lower()
        print_test("Annotate failure step", True)
        passed += 1
    except Exception as e:
        print_test("Annotate failure step", False, str(e))
    
    # Test 3: Annotate step with recovery
    total += 1
    try:
        action = {"type": "click", "target": "button"}
        outcome = {"success": True}
        failure_info = {"failure_type": "element_not_interactable", "severity": 0.6}
        recovery_info = {
            "attempted": True,
            "success": True,
            "strategy": "scroll_into_view",
        }
        
        annotation = annotator.annotate_step(2, action, outcome, failure_info, recovery_info)
        assert annotation.memory_update_flag, "Should flag recovery for memory"
        assert annotation.memory_type == MemoryType.RECOVERY
        print_test("Annotate recovery step", True)
        passed += 1
    except Exception as e:
        print_test("Annotate recovery step", False, str(e))
    
    # Test 4: Annotate full trajectory
    total += 1
    try:
        trajectory = {
            "steps": [
                {"step_id": 0, "type": "navigate", "url": "https://example.com"},
                {"step_id": 1, "type": "click", "selector": "button#accept"},
                {"step_id": 2, "type": "type", "selector": "input#search", "text": "query"},
            ]
        }
        
        annotations = annotator.annotate_trajectory(trajectory)
        assert len(annotations) == 3, f"Expected 3 annotations, got {len(annotations)}"
        assert all(isinstance(a, ReflectionAnnotation) for a in annotations)
        print_test("Annotate full trajectory", True)
        passed += 1
    except Exception as e:
        print_test("Annotate full trajectory", False, str(e))
    
    # Test 5: Introspection metadata
    total += 1
    try:
        action = {"type": "click", "target": "button"}
        outcome = {"success": True}
        
        annotation = annotator.annotate_step(3, action, outcome)
        assert annotation.introspection_metadata is not None
        assert isinstance(annotation.introspection_metadata.reasoning_type, ReasoningType)
        assert isinstance(annotation.introspection_metadata.uncertainty_source, UncertaintySource)
        print_test("Introspection metadata", True)
        passed += 1
    except Exception as e:
        print_test("Introspection metadata", False, str(e))
    
    # Test 6: Statistics collection
    total += 1
    try:
        stats = annotator.get_statistics()
        assert "total_annotations" in stats
        assert "memory_type_distribution" in stats
        assert stats["total_annotations"] > 0
        print_test("Statistics collection", True)
        passed += 1
    except Exception as e:
        print_test("Statistics collection", False, str(e))
    
    # Test 7: Save and load annotations
    total += 1
    try:
        import tempfile
        action = {"type": "click", "target": "button"}
        outcome = {"success": True}
        annotation = annotator.annotate_step(4, action, outcome)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            temp_file = Path(f.name)
        
        annotator.save_annotations([annotation], temp_file)
        loaded = annotator.load_annotations(temp_file)
        
        assert len(loaded) == 1
        assert loaded[0].step_id == annotation.step_id
        
        temp_file.unlink()
        print_test("Save and load annotations", True)
        passed += 1
    except Exception as e:
        print_test("Save and load annotations", False, str(e))
    
    return passed, total


def main() -> None:
    """Run all validation tests."""
    print(f"\n{Colors.BOLD}Task-06: Reflection Annotation - Validation Tests{Colors.RESET}")
    print("=" * 60)
    
    all_passed = 0
    all_total = 0
    
    # Run test suites
    test_suites = [
        test_schema_validation,
        test_confidence_estimation,
        test_reflection_generation,
        test_memory_signals,
        test_full_annotation,
    ]
    
    for test_suite in test_suites:
        passed, total = test_suite()
        all_passed += passed
        all_total += total
    
    # Print summary
    print(f"\n{Colors.BOLD}Summary{Colors.RESET}")
    print("=" * 60)
    pass_rate = (all_passed / all_total * 100) if all_total > 0 else 0
    
    if all_passed == all_total:
        color = Colors.GREEN
    elif pass_rate >= 80:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    
    print(f"Total: {color}{all_passed}/{all_total}{Colors.RESET} tests passed ({pass_rate:.1f}%)")
    
    if all_passed == all_total:
        print(f"\n{Colors.GREEN}✓ All tests passed!{Colors.RESET}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}✗ Some tests failed{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
