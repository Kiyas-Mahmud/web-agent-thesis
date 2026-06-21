"""
Recovery Generation Examples

Demonstrates all 5 recovery strategies:
1. RETRY - Re-execute action with backoff
2. BACKTRACK - Revert to previous state
3. ALTERNATIVE_TARGET - Try different element
4. REPLAN - Generate new action sequence
5. ABORT - Graceful termination
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from recovery_generation.recovery_engine import RecoveryEngine, RecoveryStats
from recovery_generation.recovery_schema import (
    RecoveryStrategy,
    RecoveryOutcome,
    RecoveryConfig,
)
from recovery_generation.strategy_selector import StrategySelector


def print_header(title: str) -> None:
    """Print formatted header."""
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"{'=' * 70}\n")


def print_recovery_result(attempt):
    """Print recovery attempt results."""
    print(f"Failure Type: {attempt.failure_type}")
    print(f"Failure Severity: {attempt.failure_severity:.2f}")
    print(f"Success: {'✓' if attempt.success else '✗'}")
    print(f"Total Duration: {attempt.total_duration_ms:.2f}ms")
    print(f"\nRecovery Attempts Made: {len(attempt.recovery_results)}")
    
    for i, result in enumerate(attempt.recovery_results, 1):
        print(f"\n  Attempt {i}:")
        print(f"    Strategy: {result.strategy.value}")
        print(f"    Outcome: {result.outcome.value}")
        print(f"    Actions: {len(result.actions_taken)}")
        if result.actions_taken:
            for action in result.actions_taken:
                print(f"      - {action.action_type}: {action.action_args}")
        print(f"    Success: {'✓' if result.success else '✗'}")


# ==================
# Example 1: RETRY Strategy
# ==================

def example_retry_recovery():
    """Example: Recover from a transient timeout using RETRY."""
    print_header("Example 1: RETRY Strategy - Transient Timeout Recovery")
    
    engine = RecoveryEngine()
    
    # Simulate a tool failure (timeout) that can be recovered by retrying
    failure_label = {
        "failure_type": "tool_failure",
        "severity": 0.4,  # Low severity (transient issue)
        "confidence": 0.8,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#submit-button"},
        },
        "current_state": {
            "url": "http://example.com/form",
        },
        "goal": "Submit form",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=3)
    
    print_recovery_result(attempt)
    print("\n✓ RETRY strategy is ideal for transient failures like timeouts")


# ==================
# Example 2: BACKTRACK Strategy
# ==================

def example_backtrack_recovery():
    """Example: Recover from a loop by backtracking."""
    print_header("Example 2: BACKTRACK Strategy - Loop Detection Recovery")
    
    engine = RecoveryEngine()
    
    # Simulate loop detection
    failure_label = {
        "failure_type": "loop_detected",
        "severity": 0.8,  # High severity (stuck in loop)
        "confidence": 0.9,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#next"},
        },
        "current_state": {
            "url": "http://example.com/step3",
        },
        "state_history": [
            {"url": "http://example.com/step1"},
            {"url": "http://example.com/step2"},
            {"url": "http://example.com/step3"},
        ],
        "goal": "Complete multi-step form",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=3)
    
    print_recovery_result(attempt)
    print("\n✓ BACKTRACK strategy returns to previous state when stuck in loop")


# ==================
# Example 3: ALTERNATIVE_TARGET Strategy
# ==================

def example_alternative_target_recovery():
    """Example: Recover from element not found by trying alternatives."""
    print_header("Example 3: ALTERNATIVE_TARGET Strategy - Element Not Found Recovery")
    
    engine = RecoveryEngine()
    
    # Simulate perception error (element not found)
    failure_label = {
        "failure_type": "perception_error",
        "severity": 0.6,
        "confidence": 0.7,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#submit-btn"},
        },
        "current_state": {
            "url": "http://example.com/form",
        },
        "alternative_selectors": [
            "button[type='submit']",
            ".submit-button",
            "[role='button']",
        ],
        "goal": "Click submit button",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=4)
    
    print_recovery_result(attempt)
    print("\n✓ ALTERNATIVE_TARGET tries different selectors when element not found")


# ==================
# Example 4: REPLAN Strategy
# ==================

def example_replan_recovery():
    """Example: Recover from action mismatch by replanning."""
    print_header("Example 4: REPLAN Strategy - Action Mismatch Recovery")
    
    engine = RecoveryEngine()
    
    # Simulate action mismatch (wrong action executed)
    failure_label = {
        "failure_type": "action_mismatch",
        "severity": 0.5,
        "confidence": 0.8,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#save"},
        },
        "current_state": {
            "url": "http://example.com/editor",
            "page_state": "not_saved",
        },
        "goal": "Save document",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=2)
    
    print_recovery_result(attempt)
    print("\n✓ REPLAN generates alternative action sequence when original fails")


# ==================
# Example 5: ABORT Strategy
# ==================

def example_abort_recovery():
    """Example: Abort when recovery is impossible."""
    print_header("Example 5: ABORT Strategy - Unrecoverable Failure")
    
    engine = RecoveryEngine()
    
    # Simulate goal misalignment with no recovery path
    failure_label = {
        "failure_type": "goal_misalignment",
        "severity": 0.9,  # Very high severity
        "confidence": 0.95,  # Very confident it's wrong
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": "#delete-all"},
        },
        "current_state": {
            "url": "http://example.com/admin",
        },
        "goal": "View user profile",
        "abort_reason": "Action would delete all users - wrong path",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=1)
    
    print_recovery_result(attempt)
    print("\n✓ ABORT strategy used when recovery would be unsafe or impossible")


# ==================
# Example 6: Multi-Strategy Recovery
# ==================

def example_multi_strategy_recovery():
    """Example: Try multiple strategies in sequence."""
    print_header("Example 6: Multi-Strategy Recovery - Sequential Attempts")
    
    config = RecoveryConfig(max_total_attempts=5)
    engine = RecoveryEngine(config=config)
    
    # Simulate state no change (action executed but nothing happened)
    failure_label = {
        "failure_type": "state_no_change",
        "severity": 0.6,
        "confidence": 0.7,
    }
    
    context = {
        "failed_action": {
            "type": "type",
            "args": {"selector": "#username", "text": "user123"},
        },
        "current_state": {
            "url": "http://example.com/login",
            "field_value": "",  # Field still empty
        },
        "state_history": [
            {"url": "http://example.com/"},
            {"url": "http://example.com/login"},
        ],
        "goal": "Login to application",
    }
    
    attempt = engine.recover_from_failure(failure_label, context)
    
    print_recovery_result(attempt)
    print("\n✓ Recovery engine tries multiple strategies when first one fails")


# ==================
# Example 7: Custom Strategy Mapping
# ==================

def example_custom_strategy_mapping():
    """Example: Override default strategy mappings."""
    print_header("Example 7: Custom Strategy Mapping")
    
    engine = RecoveryEngine()
    
    # Override default mapping for UI_VARIATION
    print("Default strategy for UI_VARIATION: ALTERNATIVE_TARGET → REPLAN")
    
    # Add custom mapping: prefer REPLAN first
    engine.add_custom_strategy_mapping(
        failure_type="UI_VARIATION",
        primary=RecoveryStrategy.REPLAN,
        secondary=RecoveryStrategy.ALTERNATIVE_TARGET,
        priority=100,  # High priority
    )
    
    print("Custom strategy for UI_VARIATION: REPLAN → ALTERNATIVE_TARGET")
    
    failure_label = {
        "failure_type": "ui_variation",
        "severity": 0.5,
        "confidence": 0.7,
    }
    
    context = {
        "failed_action": {
            "type": "click",
            "args": {"selector": ".submit"},
        },
        "current_state": {
            "url": "http://example.com/checkout",
        },
        "goal": "Complete checkout",
    }
    
    attempt = engine.recover_from_failure(failure_label, context, max_attempts=3)
    
    print_recovery_result(attempt)
    print("\n✓ Custom mappings allow fine-tuning recovery behavior per task")


# ==================
# Example 8: Recovery Statistics
# ==================

def example_recovery_statistics():
    """Example: Track recovery success rates."""
    print_header("Example 8: Recovery Statistics Tracking")
    
    engine = RecoveryEngine()
    
    # Simulate multiple recovery attempts
    test_cases = [
        {"failure_type": "action_mismatch", "severity": 0.5},
        {"failure_type": "perception_error", "severity": 0.6},
        {"failure_type": "state_no_change", "severity": 0.4},
        {"failure_type": "tool_failure", "severity": 0.3},
        {"failure_type": "ui_variation", "severity": 0.5},
    ]
    
    context = {
        "failed_action": {"type": "click", "args": {}},
        "current_state": {"url": "http://example.com"},
        "goal": "Test recovery",
    }
    
    for test_case in test_cases:
        engine.recover_from_failure(test_case, context, max_attempts=3)
    
    stats = engine.get_stats()
    
    print(f"Total Attempts: {stats.total_attempts}")
    print(f"Successful Recoveries: {stats.successful_recoveries}")
    print(f"Failed Recoveries: {stats.failed_recoveries}")
    print(f"Aborted Recoveries: {stats.aborted_recoveries}")
    print(f"Success Rate: {stats.get_success_rate() * 100:.1f}%")
    print(f"Average Recovery Time: {stats.avg_recovery_time_ms:.2f}ms")
    
    print("\nStrategy Usage:")
    for strategy, count in stats.strategy_attempts.items():
        successes = stats.strategy_successes.get(strategy, 0)
        success_rate = (successes / count * 100) if count > 0 else 0
        print(f"  {strategy.value}: {count} attempts, {successes} successes ({success_rate:.1f}%)")
    
    print("\n✓ Statistics help tune recovery strategy effectiveness")


# ==================
# Main Runner
# ==================

def run_all_examples():
    """Run all recovery generation examples."""
    print("\n" + "=" * 70)
    print("Task-05: Recovery Generation Examples")
    print("=" * 70)
    
    examples = [
        ("RETRY Strategy", example_retry_recovery),
        ("BACKTRACK Strategy", example_backtrack_recovery),
        ("ALTERNATIVE_TARGET Strategy", example_alternative_target_recovery),
        ("REPLAN Strategy", example_replan_recovery),
        ("ABORT Strategy", example_abort_recovery),
        ("Multi-Strategy Recovery", example_multi_strategy_recovery),
        ("Custom Strategy Mapping", example_custom_strategy_mapping),
        ("Recovery Statistics", example_recovery_statistics),
    ]
    
    for i, (name, example_func) in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Example {i} ({name}) failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✓ All examples completed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_all_examples()
