"""
Quality Gate Checker
====================
Validates dataset quality against research standards before final collection.

Quality Gates:
--------------
Gate A: error_page_rate < 2%
Gate B: success_consistency > 95%
Gate C: failure_distribution balanced (perception_error < 50%)
Gate D: recovery_execution_rate > 80%

Usage:
------
    python _quality_gates.py
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Quality gate thresholds
ERROR_PAGE_RATE_THRESHOLD = 0.02  # 2%
SUCCESS_CONSISTENCY_THRESHOLD = 0.95  # 95%
PERCEPTION_ERROR_THRESHOLD = 0.50  # 50%
RECOVERY_EXECUTION_THRESHOLD = 0.80  # 80%


def load_training_data(file_path: str) -> List[Dict[str, Any]]:
    """Load flat training JSONL data."""
    steps = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                steps.append(json.loads(line))
    return steps


def check_gate_a_error_pages(steps: List[Dict[str, Any]]) -> tuple[bool, float, str]:
    """
    Gate A: Error page rate < 2%
    
    Checks if chrome-error pages are properly detected and classified.
    """
    total = len(steps)
    if total == 0:
        return False, 0.0, "No steps to analyze"
    
    error_pages = 0
    for step in steps:
        # In the new implementation, error pages should be:
        # 1. Marked as failures (not success)
        # 2. Classified as tool_failure
        # 3. Have failure_subtype like PAGE_NOT_LOADED, TIMEOUT, DNS_ERROR
        
        outcome = step.get("execution_outcome", "").upper()
        failure_type = step.get("failure_type", "")
        
        # Check if URL is chrome-error (legacy check)
        url_after = step.get("url_after", "")
        if "chrome-error://" in url_after:
            # Should be marked as FAILURE, not SUCCESS
            if outcome == "SUCCESS":
                error_pages += 1
    
    error_rate = error_pages / total
    passed = error_rate < ERROR_PAGE_RATE_THRESHOLD
    
    status = "✅ PASS" if passed else "❌ FAIL"
    message = f"{status} Gate A - Error Page Rate: {error_rate:.1%} (threshold: <{ERROR_PAGE_RATE_THRESHOLD:.1%})"
    
    return passed, error_rate, message


def check_gate_b_success_consistency(steps: List[Dict[str, Any]]) -> tuple[bool, float, str]:
    """
    Gate B: SUCCESS consistency > 95%
    
    Checks that SUCCESS steps have actual state changes (pixel_diff > 0 OR URL changed).
    """
    success_steps = [s for s in steps if s.get("execution_outcome", "").upper() == "SUCCESS"]
    total_success = len(success_steps)
    
    if total_success == 0:
        return False, 0.0, "No SUCCESS steps to analyze"
    
    consistent_success = 0
    for step in success_steps:
        pixel_diff = step.get("pixel_diff", 0) or 0
        url_before = step.get("url_before", "")
        url_after = step.get("url_after", "")
        
        # Success should have either:
        # 1. Visual change (pixel_diff > 0.001)
        # 2. URL change
        has_visual_change = pixel_diff > 0.001
        has_url_change = url_before != url_after
        
        if has_visual_change or has_url_change:
            consistent_success += 1
    
    consistency = consistent_success / total_success
    passed = consistency > SUCCESS_CONSISTENCY_THRESHOLD
    
    status = "✅ PASS" if passed else "❌ FAIL"
    message = f"{status} Gate B - SUCCESS Consistency: {consistency:.1%} (threshold: >{SUCCESS_CONSISTENCY_THRESHOLD:.1%})"
    
    return passed, consistency, message


def check_gate_c_failure_distribution(steps: List[Dict[str, Any]]) -> tuple[bool, float, str]:
    """
    Gate C: Balanced failure distribution (perception_error < 50%)
    
    Checks that perception_error is not overused.
    """
    failure_steps = [s for s in steps if s.get("execution_outcome", "").upper() == "FAILURE"]
    total_failures = len(failure_steps)
    
    if total_failures == 0:
        return True, 0.0, "✅ PASS Gate C - No failures to analyze"
    
    failure_types = {}
    for step in failure_steps:
        ftype = step.get("failure_type", "unknown")
        failure_types[ftype] = failure_types.get(ftype, 0) + 1
    
    perception_errors = failure_types.get("perception_error", 0)
    perception_rate = perception_errors / total_failures
    
    passed = perception_rate < PERCEPTION_ERROR_THRESHOLD
    
    status = "✅ PASS" if passed else "❌ FAIL"
    message = (
        f"{status} Gate C - Failure Distribution:\n"
        f"  perception_error: {perception_rate:.1%} (threshold: <{PERCEPTION_ERROR_THRESHOLD:.1%})\n"
    )
    
    # Add breakdown
    for ftype, count in sorted(failure_types.items(), key=lambda x: -x[1]):
        rate = count / total_failures
        message += f"    - {ftype}: {count} ({rate:.1%})\n"
    
    return passed, perception_rate, message


def check_gate_d_recovery_execution(steps: List[Dict[str, Any]]) -> tuple[bool, float, str]:
    """
    Gate D: Recovery execution rate > 80%
    
    Checks that recovery strategies are actually attempted (not just suggested).
    """
    steps_with_recovery_strategy = [
        s for s in steps 
        if s.get("recovery_strategy") is not None
    ]
    total_recoverable = len(steps_with_recovery_strategy)
    
    if total_recoverable == 0:
        return True, 0.0, "✅ PASS Gate D - No recoverable failures to analyze"
    
    # Count steps where recovery_success is not null (meaning recovery was attempted and measured)
    recovery_executed = sum(
        1 for s in steps_with_recovery_strategy
        if s.get("recovery_success") is not None
    )
    
    execution_rate = recovery_executed / total_recoverable
    passed = execution_rate > RECOVERY_EXECUTION_THRESHOLD
    
    status = "✅ PASS" if passed else "❌ FAIL"
    message = (
        f"{status} Gate D - Recovery Execution Rate: {execution_rate:.1%} "
        f"(threshold: >{RECOVERY_EXECUTION_THRESHOLD:.1%})\n"
        f"  Recoverable failures: {total_recoverable}\n"
        f"  Recovery executed: {recovery_executed}"
    )
    
    return passed, execution_rate, message


def main():
    """Run all quality gate checks."""
    print("=" * 70)
    print("QUALITY GATE VALIDATION")
    print("=" * 70)
    print()
    
    # Load data
    data_file = "dataset/collected/mind2web_training.jsonl"
    if not Path(data_file).exists():
        print(f"❌ ERROR: {data_file} not found")
        print("Run collection first: python src/collection_runner/collect_runner.py")
        return
    
    steps = load_training_data(data_file)
    print(f"Loaded {len(steps)} steps from {data_file}")
    print()
    
    # Run gates
    results = []
    
    print("Running quality gates...")
    print("-" * 70)
    
    # Gate A
    pass_a, rate_a, msg_a = check_gate_a_error_pages(steps)
    print(msg_a)
    results.append(("Gate A", pass_a))
    print()
    
    # Gate B
    pass_b, rate_b, msg_b = check_gate_b_success_consistency(steps)
    print(msg_b)
    results.append(("Gate B", pass_b))
    print()
    
    # Gate C
    pass_c, rate_c, msg_c = check_gate_c_failure_distribution(steps)
    print(msg_c)
    results.append(("Gate C", pass_c))
    print()
    
    # Gate D
    pass_d, rate_d, msg_d = check_gate_d_recovery_execution(steps)
    print(msg_d)
    results.append(("Gate D", pass_d))
    print()
    
    # Final verdict
    print("=" * 70)
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("✅ ALL GATES PASSED - Dataset ready for final collection")
    else:
        print("❌ QUALITY GATES FAILED")
        print()
        print("Failed gates:")
        for gate_name, passed in results:
            if not passed:
                print(f"  - {gate_name}")
        print()
        print("Fix issues before running final 200-task collection.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
