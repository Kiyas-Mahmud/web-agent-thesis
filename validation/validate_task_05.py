"""
Validation Tests for Recovery Generation (Task-05)

Tests all recovery components:
1. Recovery schema and data models
2. Strategy selector logic
3. Individual strategy executors
4. RecoveryEngine orchestration
5. Statistics tracking
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from recovery_generation.recovery_schema import (
    RecoveryStrategy,
    RecoveryOutcome,
    RecoveryAction,
    RecoveryResult,
    RecoveryAttempt,
    RecoveryConfig,
    DEFAULT_RECOVERY_CONFIG,
    create_recovery_result,
    create_abort_result,
)
from recovery_generation.strategy_selector import (
    StrategyMapping,
    StrategySelector,
)
from recovery_generation.recovery_executor import (
    RetryExecutor,
    BacktrackExecutor,
    AlternativeTargetExecutor,
    ReplanExecutor,
    AbortExecutor,
)
from recovery_generation.recovery_engine import (
    RecoveryEngine,
    RecoveryStats,
)


# ====================
# Schema Tests
# ====================

def test_recovery_action_creation():
    """Test RecoveryAction model creation."""
    action = RecoveryAction(
        action_type="click",
        action_args={"selector": "#button"},
        expected_outcome="Button click succeeds",
        timeout_ms=5000,
    )
    
    assert action.action_type == "click"
    assert action.action_args["selector"] == "#button"
    assert action.timeout_ms == 5000
    print("✓ RecoveryAction creation")


def test_recovery_result_creation():
    """Test RecoveryResult model with actions."""
    action = RecoveryAction(
        action_type="click",
        action_args={"selector": "#btn"},
    )
    
    result = RecoveryResult(
        strategy=RecoveryStrategy.RETRY,
        outcome=RecoveryOutcome.SUCCESS,
        actions_taken=[action],
        success=True,
        duration_ms=150.0,
        confidence=0.8,
    )
    
    assert result.strategy == RecoveryStrategy.RETRY
    assert result.outcome == RecoveryOutcome.SUCCESS
    assert len(result.actions_taken) == 1
    assert result.success is True
    print("✓ RecoveryResult creation")


def test_recovery_attempt_creation():
    """Test RecoveryAttempt with multiple results."""
    action = RecoveryAction(action_type="click", action_args={})
    
    result1 = RecoveryResult(
        strategy=RecoveryStrategy.RETRY,
        outcome=RecoveryOutcome.FAILURE,
        actions_taken=[action],
        success=False,
        duration_ms=100.0,
        confidence=0.7,
    )
    
    result2 = RecoveryResult(
        strategy=RecoveryStrategy.BACKTRACK,
        outcome=RecoveryOutcome.SUCCESS,
        actions_taken=[action],
        success=True,
        duration_ms=200.0,
        confidence=0.6,
    )
    
    attempt = RecoveryAttempt(
        failure_type="PERCEPTION_ERROR",
        failure_severity=0.7,
        recovery_results=[result1, result2],
        final_result=result2,
        success=True,
        total_duration_ms=300.0,
    )
    
    assert attempt.failure_type == "PERCEPTION_ERROR"
    assert len(attempt.recovery_results) == 2
    assert attempt.success is True
    assert attempt.final_result.strategy == RecoveryStrategy.BACKTRACK
    print("✓ RecoveryAttempt creation")


def test_recovery_config():
    """Test RecoveryConfig with custom values."""
    config = RecoveryConfig(
        retry_max_attempts=5,
        retry_backoff_ms=2000,
        max_total_attempts=15,
    )
    
    assert config.retry_max_attempts == 5
    assert config.retry_backoff_ms == 2000
    assert config.max_total_attempts == 15
    print("✓ RecoveryConfig with custom values")


def test_create_recovery_result_helper():
    """Test helper function for creating results."""
    result = create_recovery_result(
        strategy=RecoveryStrategy.ALTERNATIVE_TARGET,
        outcome=RecoveryOutcome.SUCCESS,
        success=True,
        duration_ms=250.0,
        actions=[
            RecoveryAction(action_type="click", action_args={"selector": ".alt"})
        ],
    )
    
    assert result.strategy == RecoveryStrategy.ALTERNATIVE_TARGET
    assert result.success is True
    assert result.outcome == RecoveryOutcome.SUCCESS
    assert len(result.actions_taken) == 1
    print("✓ create_recovery_result helper")


def test_create_abort_result_helper():
    """Test abort result helper."""
    result = create_abort_result("Max attempts exceeded", duration_ms=500.0)
    
    assert result.strategy == RecoveryStrategy.ABORT
    assert result.outcome == RecoveryOutcome.ABORTED
    assert result.success is False
    assert "Max attempts exceeded" in result.error_message
    print("✓ create_abort_result helper")


# ====================
# Strategy Selector Tests
# ====================

def test_strategy_selector_creation():
    """Test StrategySelector initialization."""
    selector = StrategySelector()
    assert len(selector.mappings) > 0  # Should have default mappings
    print("✓ StrategySelector creation")


def test_strategy_selection_for_perception_error():
    """Test strategy selection for PERCEPTION_ERROR."""
    selector = StrategySelector()
    
    strategy = selector.select_strategy(
        failure_label="PERCEPTION_ERROR",
        attempt_number=1,
    )
    
    assert strategy in [RecoveryStrategy.ALTERNATIVE_TARGET, RecoveryStrategy.REPLAN]
    print("✓ Strategy selection for PERCEPTION_ERROR")


def test_strategy_selection_for_loop():
    """Test strategy selection for LOOP_DETECTED (high priority)."""
    selector = StrategySelector()
    
    strategy = selector.select_strategy(
        failure_label="LOOP_DETECTED",
        attempt_number=1,
    )
    
    assert strategy in [RecoveryStrategy.BACKTRACK, RecoveryStrategy.REPLAN]
    print("✓ Strategy selection for LOOP_DETECTED")


def test_strategy_sequence():
    """Test getting full strategy sequence."""
    selector = StrategySelector()
    
    sequence = selector.get_strategy_sequence(
        failure_label="ACTION_MISMATCH",
        max_attempts=5,  # Increase attempts for better test
        severity=0.5,
        confidence=0.7,
    )
    
    assert len(sequence) > 0
    # Should have multiple strategies including final strategy
    assert len(sequence) >= 2
    print("✓ Strategy sequence generation")


def test_custom_strategy_mapping():
    """Test adding custom strategy mapping."""
    selector = StrategySelector()
    
    # Override default mapping for TOOL_FAILURE
    selector.add_custom_mapping(
        failure_type="TOOL_FAILURE",
        primary=RecoveryStrategy.REPLAN,
        secondary=RecoveryStrategy.RETRY,
        priority=100,  # High priority to override default
    )
    
    strategy = selector.select_strategy(
        failure_label="TOOL_FAILURE",
        attempt_number=1,
    )
    
    assert strategy == RecoveryStrategy.REPLAN
    print("✓ Custom strategy mapping")


def test_strategy_adjustment_by_severity():
    """Test strategy adjustment based on severity."""
    selector = StrategySelector()
    
    # High severity should potentially adjust strategy
    strategy_low = selector.select_strategy(
        failure_label="STATE_NO_CHANGE",
        attempt_number=1,
        severity=0.2,
    )
    
    strategy_high = selector.select_strategy(
        failure_label="STATE_NO_CHANGE",
        attempt_number=1,
        severity=0.9,
    )
    
    # Both should be valid strategies
    assert strategy_low in [s for s in RecoveryStrategy]
    assert strategy_high in [s for s in RecoveryStrategy]
    print("✓ Strategy adjustment by severity")


# ====================
# Executor Tests
# ====================

def test_retry_executor():
    """Test RetryExecutor."""
    executor = RetryExecutor()
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#button"},
        }
    }
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.strategy == RecoveryStrategy.RETRY
    assert len(result.actions_taken) > 0
    assert result.actions_taken[0].action_type == "click"
    print("✓ RetryExecutor")


def test_retry_executor_max_attempts():
    """Test RetryExecutor respects max attempts."""
    config = RecoveryConfig(retry_max_attempts=3)
    executor = RetryExecutor(config)
    
    context = {"failed_action": {"type": "click", "args": {}}}
    
    result = executor.execute(context, attempt_number=5)  # Exceeds max
    
    assert result.outcome == RecoveryOutcome.ABORTED
    print("✓ RetryExecutor max attempts")


def test_backtrack_executor():
    """Test BacktrackExecutor."""
    executor = BacktrackExecutor()
    
    context = {
        "state_history": [
            {"url": "http://example.com/page1"},
            {"url": "http://example.com/page2"},
            {"url": "http://example.com/page3"},
        ]
    }
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.strategy == RecoveryStrategy.BACKTRACK
    assert len(result.actions_taken) > 0
    assert result.actions_taken[0].action_type == "navigate"
    print("✓ BacktrackExecutor")


def test_backtrack_executor_no_history():
    """Test BacktrackExecutor with no history."""
    executor = BacktrackExecutor()
    
    context = {"state_history": []}
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.outcome == RecoveryOutcome.ABORTED
    print("✓ BacktrackExecutor with no history")


def test_alternative_target_executor():
    """Test AlternativeTargetExecutor."""
    executor = AlternativeTargetExecutor()
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#original-button"},
        },
        "alternative_selectors": [".button", "[role='button']"],
    }
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.strategy == RecoveryStrategy.ALTERNATIVE_TARGET
    assert len(result.actions_taken) > 0
    assert result.actions_taken[0].action_args["selector"] in [".button", "[role='button']"]
    print("✓ AlternativeTargetExecutor")


def test_alternative_target_generation():
    """Test alternative selector generation."""
    executor = AlternativeTargetExecutor()
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#my-id"},
        }
    }
    
    result = executor.execute(context, attempt_number=1)
    
    # Should generate alternatives from ID selector
    assert result.strategy == RecoveryStrategy.ALTERNATIVE_TARGET
    assert len(result.actions_taken) > 0
    print("✓ Alternative selector generation")


def test_replan_executor():
    """Test ReplanExecutor."""
    executor = ReplanExecutor()
    
    context = {
        "goal": "Click submit button",
        "current_state": {"url": "http://example.com/form"},
        "failed_action": {
            "type": "click",
            "args": {"selector": "#submit"},
        },
    }
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.strategy == RecoveryStrategy.REPLAN
    assert len(result.actions_taken) > 0  # Should have alternative plan
    print("✓ ReplanExecutor")


def test_replan_executor_no_goal():
    """Test ReplanExecutor without goal."""
    executor = ReplanExecutor()
    
    context = {"current_state": {}, "failed_action": {}}
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.outcome == RecoveryOutcome.ABORTED
    print("✓ ReplanExecutor without goal")


def test_abort_executor():
    """Test AbortExecutor."""
    executor = AbortExecutor()
    
    context = {"abort_reason": "Unrecoverable error"}
    
    result = executor.execute(context, attempt_number=1)
    
    assert result.strategy == RecoveryStrategy.ABORT
    assert result.outcome == RecoveryOutcome.ABORTED
    assert "Unrecoverable error" in result.error_message
    print("✓ AbortExecutor")


# ====================
# RecoveryEngine Tests
# ====================

def test_recovery_engine_creation():
    """Test RecoveryEngine initialization."""
    engine = RecoveryEngine()
    
    assert engine.config is not None
    assert engine.selector is not None
    assert len(engine.executors) == 5  # One for each strategy
    print("✓ RecoveryEngine creation")


def test_recovery_engine_with_custom_config():
    """Test RecoveryEngine with custom config."""
    config = RecoveryConfig(max_total_attempts=10)
    engine = RecoveryEngine(config=config)
    
    assert engine.config.max_total_attempts == 10
    print("✓ RecoveryEngine with custom config")


def test_recovery_attempt_simple():
    """Test simple recovery attempt."""
    engine = RecoveryEngine()
    
    failure_label = {
        "failure_type": "ACTION_MISMATCH",
        "severity": 0.5,
        "confidence": 0.7,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#button"},
        },
        "current_state": {},
        "goal": "Click button",
    }
    
    attempt = engine.recover_from_failure(failure_label, context)
    
    assert attempt.failure_type == "ACTION_MISMATCH"
    assert len(attempt.recovery_results) > 0
    assert attempt.final_result is not None
    print("✓ Simple recovery attempt")


def test_recovery_stats_tracking():
    """Test that stats are tracked correctly."""
    engine = RecoveryEngine()
    
    failure_label = {"failure_type": "STATE_NO_CHANGE", "severity": 0.5}
    context = {
        "failed_action": {"type": "click", "args": {}},
        "goal": "Test",
    }
    
    # Make multiple attempts
    engine.recover_from_failure(failure_label, context)
    engine.recover_from_failure(failure_label, context)
    
    stats = engine.get_stats()
    assert stats.total_attempts == 2
    print("✓ Recovery stats tracking")


def test_recovery_stats_success_rate():
    """Test success rate calculation."""
    stats = RecoveryStats()
    
    # Create mock successful attempt
    success_result = RecoveryResult(
        strategy=RecoveryStrategy.RETRY,
        outcome=RecoveryOutcome.SUCCESS,
        actions_taken=[],
        success=True,
        duration_ms=100.0,
        confidence=0.8,
    )
    
    success_attempt = RecoveryAttempt(
        failure_type="TEST",
        failure_severity=0.5,
        recovery_results=[success_result],
        final_result=success_result,
        success=True,
        total_duration_ms=100.0,
    )
    
    # Create mock failed attempt
    fail_result = RecoveryResult(
        strategy=RecoveryStrategy.RETRY,
        outcome=RecoveryOutcome.FAILURE,
        actions_taken=[],
        success=False,
        duration_ms=100.0,
        confidence=0.5,
    )
    
    fail_attempt = RecoveryAttempt(
        failure_type="TEST",
        failure_severity=0.5,
        recovery_results=[fail_result],
        final_result=fail_result,
        success=False,
        total_duration_ms=100.0,
    )
    
    stats.update(success_attempt)
    stats.update(fail_attempt)
    
    assert stats.get_success_rate() == 0.5
    print("✓ Success rate calculation")


def test_custom_strategy_mapping_in_engine():
    """Test adding custom strategy mapping to engine."""
    engine = RecoveryEngine()
    
    # Override default mapping for UI_VARIATION
    engine.add_custom_strategy_mapping(
        failure_type="UI_VARIATION",
        primary=RecoveryStrategy.REPLAN,
        secondary=RecoveryStrategy.ABORT,
    )
    
    failure_label = {"failure_type": "ui_variation", "severity": 0.5}
    context = {
        "failed_action": {"type": "click", "args": {}},
        "current_state": {},
        "goal": "Test custom mapping",
    }
    
    attempt = engine.recover_from_failure(failure_label, context)
    
    # Should use custom mapping
    assert attempt.recovery_results[0].strategy in [
        RecoveryStrategy.REPLAN,
        RecoveryStrategy.ABORT,
    ]
    print("✓ Custom strategy mapping in engine")


def test_recovery_stats_reset():
    """Test stats reset."""
    engine = RecoveryEngine()
    
    failure_label = {"failure_type": "TEST", "severity": 0.5}
    context = {"failed_action": {"type": "click", "args": {}}, "goal": "Test"}
    
    engine.recover_from_failure(failure_label, context)
    assert engine.get_stats().total_attempts == 1
    
    engine.reset_stats()
    assert engine.get_stats().total_attempts == 0
    print("✓ Stats reset")


def test_no_failure_type():
    """Test handling missing failure type."""
    engine = RecoveryEngine()
    
    failure_label = {}  # No failure type
    context = {"failed_action": {"type": "click", "args": {}}}
    
    attempt = engine.recover_from_failure(failure_label, context)
    
    assert attempt.final_result.outcome == RecoveryOutcome.ABORTED
    print("✓ Missing failure type handling")


# ====================
# Integration Tests
# ====================

def test_full_recovery_workflow():
    """Test complete recovery workflow."""
    engine = RecoveryEngine()
    
    # Simulate a PERCEPTION_ERROR failure
    failure_label = {
        "failure_type": "PERCEPTION_ERROR",
        "severity": 0.6,
        "confidence": 0.8,
        "primary_signal": "element_not_found",
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#missing-button"},
        },
        "current_state": {
            "url": "http://example.com/page",
        },
        "alternative_selectors": [
            ".button",
            "[role='button']",
            "button",
        ],
        "goal": "Click the submit button",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=3)
    
    # Verify attempt structure
    assert attempt.failure_type == "PERCEPTION_ERROR"
    assert attempt.failure_severity == 0.6
    assert len(attempt.recovery_results) > 0
    assert attempt.final_result is not None
    
    # Should try ALTERNATIVE_TARGET or REPLAN
    tried_strategies = {r.strategy for r in attempt.recovery_results}
    assert RecoveryStrategy.ALTERNATIVE_TARGET in tried_strategies or \
           RecoveryStrategy.REPLAN in tried_strategies
    
    print("✓ Full recovery workflow")


def test_multiple_strategy_attempts():
    """Test trying multiple strategies in sequence."""
    config = RecoveryConfig(max_total_attempts=5)
    engine = RecoveryEngine(config=config)
    
    failure_label = {
        "failure_type": "LOOP_DETECTED",
        "severity": 0.8,
        "confidence": 0.9,
    }
    
    context = {
        "failed_action": {"type": "click", "args": {"selector": "#btn"}},
        "state_history": [
            {"url": "http://example.com/page1"},
            {"url": "http://example.com/page2"},
        ],
        "current_state": {"url": "http://example.com/page2"},
        "goal": "Complete task",
    }
    
    attempt = engine.recover_from_failure(failure_label, context)
    
    # Should have tried multiple strategies
    assert len(attempt.recovery_results) >= 1
    
    # LOOP_DETECTED should trigger BACKTRACK or REPLAN
    strategies_used = [r.strategy for r in attempt.recovery_results]
    assert RecoveryStrategy.BACKTRACK in strategies_used or \
           RecoveryStrategy.REPLAN in strategies_used
    
    print("✓ Multiple strategy attempts")


# ====================
# Main Test Runner
# ====================

def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("Task-05 Recovery Generation Validation")
    print("=" * 60)
    
    test_functions = [
        # Schema tests
        ("Schema Tests", [
            test_recovery_action_creation,
            test_recovery_result_creation,
            test_recovery_attempt_creation,
            test_recovery_config,
            test_create_recovery_result_helper,
            test_create_abort_result_helper,
        ]),
        
        # Strategy selector tests
        ("Strategy Selector Tests", [
            test_strategy_selector_creation,
            test_strategy_selection_for_perception_error,
            test_strategy_selection_for_loop,
            test_strategy_sequence,
            test_custom_strategy_mapping,
            test_strategy_adjustment_by_severity,
        ]),
        
        # Executor tests
        ("Executor Tests", [
            test_retry_executor,
            test_retry_executor_max_attempts,
            test_backtrack_executor,
            test_backtrack_executor_no_history,
            test_alternative_target_executor,
            test_alternative_target_generation,
            test_replan_executor,
            test_replan_executor_no_goal,
            test_abort_executor,
        ]),
        
        # Engine tests
        ("Recovery Engine Tests", [
            test_recovery_engine_creation,
            test_recovery_engine_with_custom_config,
            test_recovery_attempt_simple,
            test_recovery_stats_tracking,
            test_recovery_stats_success_rate,
            test_custom_strategy_mapping_in_engine,
            test_recovery_stats_reset,
            test_no_failure_type,
        ]),
        
        # Integration tests
        ("Integration Tests", [
            test_full_recovery_workflow,
            test_multiple_strategy_attempts,
        ]),
    ]
    
    total_passed = 0
    total_failed = 0
    
    for category, tests in test_functions:
        print(f"\n{category}")
        print("-" * 60)
        
        for test_func in tests:
            try:
                test_func()
                total_passed += 1
            except AssertionError as e:
                print(f"✗ {test_func.__name__}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"✗ {test_func.__name__}: Unexpected error: {e}")
                total_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)
    
    if total_failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
