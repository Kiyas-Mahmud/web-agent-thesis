"""
Example: Using Reflection Annotation System

Demonstrates how to annotate trajectories with introspective annotations.
"""

import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from reflection_annotation import (
    ReflectionAnnotator,
    ReflectionConfig,
    MemoryType,
)


def example_simple_annotation():
    """Example: Annotate a single step"""
    print("\n=== Simple Step Annotation ===\n")
    
    annotator = ReflectionAnnotator()
    
    # Action information
    action = {
        "type": "click",
        "target": "button#submit",
        "element_found": True,
    }
    
    # Outcome information
    outcome = {
        "success": True,
        "page_loaded": True,
        "state_changed": True,
    }
    
    # Metrics (from Task-03)
    metrics = {
        "visual": {"pixel_diff": 0.25},
        "state_hash": {"changed": True},
    }
    
    # Create annotation
    annotation = annotator.annotate_step(
        step_id=0,
        action=action,
        outcome=outcome,
        metrics=metrics,
    )
    
    # Print results
    print(f"Step ID: {annotation.step_id}")
    print(f"Confidence Before: {annotation.agent_confidence_before:.2f}")
    print(f"Confidence After: {annotation.agent_confidence_after:.2f}")
    print(f"Confidence Delta: {annotation.confidence_delta:+.2f}")
    print(f"Reflection: {annotation.reflection_text}")
    print(f"Memory Update: {annotation.memory_update_flag}")
    print(f"Memory Type: {annotation.memory_type.value}")


def example_failure_annotation():
    """Example: Annotate a failed step"""
    print("\n=== Failure Annotation ===\n")
    
    annotator = ReflectionAnnotator()
    
    # Action information
    action = {
        "type": "type",
        "target": "input#email",
        "element_found": False,
    }
    
    # Outcome information
    outcome = {
        "success": False,
        "timeout": True,
    }
    
    # Failure info (from Task-04)
    failure_info = {
        "failure_type": "element_not_found",
        "severity": 0.9,
        "confidence": 0.95,
        "primary_signal": "no_visual_change",
    }
    
    # Create annotation
    annotation = annotator.annotate_step(
        step_id=1,
        action=action,
        outcome=outcome,
        failure_info=failure_info,
    )
    
    # Print results
    print(f"Step ID: {annotation.step_id}")
    print(f"Confidence Before: {annotation.agent_confidence_before:.2f}")
    print(f"Confidence After: {annotation.agent_confidence_after:.2f}")
    print(f"Confidence Delta: {annotation.confidence_delta:+.2f}")
    print(f"Reflection: {annotation.reflection_text}")
    print(f"Memory Update: {annotation.memory_update_flag}")
    print(f"Memory Type: {annotation.memory_type.value}")
    print(f"Reasoning: {annotation.introspection_metadata.reasoning_type.value}")
    print(f"Uncertainty: {annotation.introspection_metadata.uncertainty_source.value}")


def example_recovery_annotation():
    """Example: Annotate a recovery attempt"""
    print("\n=== Recovery Annotation ===\n")
    
    annotator = ReflectionAnnotator()
    
    # Action information
    action = {
        "type": "click",
        "target": "button#next",
       "element_found": True,
    }
    
    # Outcome information
    outcome = {
        "success": True,
        "state_changed": True,
    }
    
    # Failure info
    failure_info = {
        "failure_type": "element_not_interactable",
        "severity": 0.7,
        "confidence": 0.85,
    }
    
    # Recovery info (from Task-05)
    recovery_info = {
        "attempted": True,
        "success": True,
        "strategy": "scroll_into_view",
        "attempts": 1,
    }
    
    # Metrics
    metrics = {
        "visual": {"pixel_diff": 0.18},
        "state_hash": {"changed": True},
    }
    
    # Create annotation
    annotation = annotator.annotate_step(
        step_id=2,
        action=action,
        outcome=outcome,
        failure_info=failure_info,
        recovery_info=recovery_info,
        metrics=metrics,
    )
    
    # Print results
    print(f"Step ID: {annotation.step_id}")
    print(f"Confidence Before: {annotation.agent_confidence_before:.2f}")
    print(f"Confidence After: {annotation.agent_confidence_after:.2f}")
    print(f"Confidence Delta: {annotation.confidence_delta:+.2f}")
    print(f"Reflection: {annotation.reflection_text}")
    print(f"Memory Update: {annotation.memory_update_flag}")
    print(f"Memory Type: {annotation.memory_type.value}")
    print(f"Reasoning: {annotation.introspection_metadata.reasoning_type.value}")
    print(f"Learning Signal: {annotation.introspection_metadata.learning_signal}")


def example_trajectory_annotation():
    """Example: Annotate full trajectory"""
    print("\n=== Full Trajectory Annotation ===\n")
    
    annotator = ReflectionAnnotator()
    
    # Trajectory with multiple steps
    trajectory = {
        "task_id": "test-001",
        "steps": [
            {
                "step_id": 0,
                "type": "navigate",
                "url": "https://example.com",
                "success": True,
            },
            {
                "step_id": 1,
                "type": "click",
                "selector": "button#accept",
                "success": True,
                "metrics": {
                    "visual": {"pixel_diff": 0.15},
                },
            },
            {
                "step_id": 2,
                "type": "type",
                "selector": "input#search",
                "text": "query",
                "success": True,
            },
        ],
    }
    
    # Annotate all steps
    annotations = annotator.annotate_trajectory(trajectory)
    
    print(f"Annotated {len(annotations)} steps")
    print()
    
    # Show summary
    for ann in annotations:
        print(f"Step {ann.step_id}:")
        print(f"  Confidence: {ann.agent_confidence_before:.2f} → {ann.agent_confidence_after:.2f}")
        print(f"  Reflection: {ann.reflection_text[:60]}...")
        print(f"  Memory: {ann.memory_type.value}")
        print()
    
    # Get statistics
    stats = annotator.get_statistics()
    print("Statistics:")
    print(f"  Total annotations: {stats['total_annotations']}")
    print(f"  Memory type distribution: {stats['memory_type_distribution']}")
    print(f"  Confidence stats: {stats['confidence_statistics']}")


def example_config_customization():
    """Example: Custom configuration"""
    print("\n=== Custom Configuration ===\n")
    
    # Create custom config
    config = ReflectionConfig(
        base_confidence=0.75,  # Lower base confidence
        confidence_threshold=0.65,
        high_confidence_threshold=0.85,
        element_not_found_penalty=0.4,  # Larger penalty
        max_reflection_length=150,  # Shorter reflections
    )
    
    annotator = ReflectionAnnotator(config)
    
    # Annotate with custom config
    action = {"type": "click", "target": "button"}
    outcome = {"success": True}
    
    annotation = annotator.annotate_step(0, action, outcome)
    
    print(f"Base Confidence: {config.base_confidence}")
    print(f"Annotation Confidence Before: {annotation.agent_confidence_before:.2f}")
    print(f"Max Reflection Length: {config.max_reflection_length}")
    print(f"Reflection Length: {len(annotation.reflection_text)}")


def example_memory_patterns():
    """Example: Memory update patterns"""
    print("\n=== Memory Update Patterns ===\n")
    
    annotator = ReflectionAnnotator()
    
    # Scenario 1: Novel failure (should trigger memory)
    print("1. Novel Failure:")
    ann1 = annotator.annotate_step(
        0,
        {"type": "click", "target": "button"},
        {"success": False},
        failure_info={"failure_type": "timeout", "severity": 0.8, "confidence": 0.9},
    )
    print(f"   Memory Update: {ann1.memory_update_flag} ({ann1.memory_type.value})")
    
    # Scenario 2: Successful recovery (should trigger memory)
    print("2. Successful Recovery:")
    ann2 = annotator.annotate_step(
        1,
        {"type": "click", "target": "button"},
        {"success": True},
        recovery_info={"attempted": True, "success": True, "strategy": "wait_and_retry"},
    )
    print(f"   Memory Update: {ann2.memory_update_flag} ({ann2.memory_type.value})")
    
    # Scenario 3: High uncertainty (should trigger memory)
    print("3. High Uncertainty:")
    ann3 = annotator.annotate_step(
        2,
        {"type": "type", "target": "input", "element_found": False},
        {"success": False},
    )
    print(f"   Memory Update: {ann3.memory_update_flag} ({ann3.memory_type.value})")
    
    # Scenario 4: Routine success (should NOT trigger memory)
    print("4. Routine Success:")
    ann4 = annotator.annotate_step(
        3,
        {"type": "click", "target": "button", "element_found": True},
        {"success": True, "state_changed": True},
        metrics={"visual": {"pixel_diff": 0.2}},
    )
    print(f"   Memory Update: {ann4.memory_update_flag} ({ann4.memory_type.value})")
    
    # Memory statistics
    stats = annotator.get_statistics()
    print(f"\nMemory Statistics:")
    print(f"  Total annotations: {stats['total_annotations']}")
    print(f"  Memory signals: {stats['memory_statistics']['memory_signals']}")
    print(f"  Memory rate: {stats['memory_statistics']['memory_rate']:.1%}")


def main():
    """Run all examples"""
    print("=" * 70)
    print("Task-06: Reflection Annotation - Examples")
    print("=" * 70)
    
    example_simple_annotation()
    example_failure_annotation()
    example_recovery_annotation()
    example_trajectory_annotation()
    example_config_customization()
    example_memory_patterns()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
