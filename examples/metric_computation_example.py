"""
Example: Using Metric Computation

Demonstrates how to use the MetricComputer to analyze trajectories.
"""

import asyncio
import sys
from pathlib import Path
import tempfile
from PIL import Image
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from metric_computation import (
    MetricComputer,
    VisualMetricsComputer,
    StateHashComputer,
    MetricThresholds
)


def create_sample_images():
    """Create sample images for demonstration"""
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Creating sample images in {temp_dir}")
    
    # Create before image
    before_img = Image.new('RGB', (400, 300), (240, 240, 240))
    before_path = temp_dir / 'before.png'
    before_img.save(before_path)
    
    # Create slightly different after image
    after_arr = np.array(before_img)
    after_arr[100:200, 150:250] = [200, 100, 100]  # Add red box
    after_img = Image.fromarray(after_arr.astype('uint8'))
    after_path = temp_dir / 'after.png'
    after_img.save(after_path)
    
    return temp_dir, before_path, after_path


def example_visual_metrics():
    """Example: Computing visual difference metrics"""
    print("=" * 70)
    print("EXAMPLE 1: Visual Metrics Computation")
    print("=" * 70)
    
    # Create test images
    temp_dir, before_path, after_path = create_sample_images()
    
    try:
        # Create visual metrics computer
        computer = VisualMetricsComputer()
        
        # Compute metrics
        print("\nComputing visual metrics...")
        metrics = computer.compute_metrics(before_path, after_path)
        
        # Display results
        print(f"\n✓ Pixel Difference Score: {metrics.pixel_diff_score:.4f}")
        print(f"✓ SSIM Score: {metrics.ssim_score:.4f}")
        print(f"✓ MSE: {metrics.mse:.2f}")
        print(f"✓ Change Level: {metrics.change_level.value}")
        print(f"✓ Computation Time: {metrics.computation_time_ms:.2f}ms")
        
        # Get change regions
        num_changed, percentage = computer.get_change_regions(before_path, after_path)
        print(f"\n✓ Changed Pixels: {num_changed} ({percentage:.2f}%)")
        
        # Create visualization
        diff_img = computer.visualize_diff(before_path, after_path, temp_dir / 'diff.png')
        print(f"✓ Difference visualization saved to {temp_dir / 'diff.png'}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 70)


def example_state_hashing():
    """Example: State hashing and loop detection"""
    print("\nEXAMPLE 2: State Hashing and Loop Detection")
    print("=" * 70)
    
    temp_dir, before_path, after_path = create_sample_images()
    
    try:
        # Create state hash computer
        computer = StateHashComputer()
        
        # Hash first state
        print("\nHashing first state...")
        hash1 = computer.compute_hashes(before_path)
        print(f"✓ State Hash: {hash1.state_hash[:16]}...")
        print(f"✓ Perceptual Hash: {hash1.perceptual_hash}")
        print(f"✓ Is Duplicate: {hash1.is_duplicate}")
        
        # Hash second state
        print("\nHashing second state...")
        hash2 = computer.compute_hashes(after_path)
        print(f"✓ State Hash: {hash2.state_hash[:16]}...")
        print(f"✓ Perceptual Hash Diff: {hash2.perceptual_hash_diff}")
        print(f"✓ Is Duplicate: {hash2.is_duplicate}")
        
        # Simulate loop
        print("\nSimulating loop (repeating first state)...")
        for i in range(4):
            hash_metrics = computer.compute_hashes(before_path)
            print(f"  Iteration {i+1}: Occurrences={hash_metrics.state_occurrences}, Loop={hash_metrics.loop_detected}")
        
        # Get summary
        summary = computer.get_state_summary()
        print(f"\n✓ Total States: {summary['total_states']}")
        print(f"✓ Unique States: {summary['unique_states']}")
        print(f"✓ Duplicate States: {summary['duplicate_states']}")
        print(f"✓ Loop States: {summary['loop_states']}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 70)


def example_step_metrics():
    """Example: Computing complete step metrics"""
    print("\nEXAMPLE 3: Complete Step Metrics")
    print("=" * 70)
    
    temp_dir, before_path, after_path = create_sample_images()
    
    try:
        # Create metric computer
        computer = MetricComputer(output_dir=str(temp_dir))
        
        # Compute step metrics
        print("\nComputing step metrics...")
        step_metrics = computer.compute_step_metrics(
            step_id=1,
            before_screenshot=before_path,
            after_screenshot=after_path,
            execution_time_ms=150.5,
            stability_wait_ms=2000.0
        )
        
        # Display results
        print(f"\n✓ Step ID: {step_metrics.step_id}")
        
        if step_metrics.visual:
            print(f"\nVisual Metrics:")
            print(f"  - Pixel Diff: {step_metrics.visual.pixel_diff_score:.4f}")
            print(f"  - SSIM: {step_metrics.visual.ssim_score:.4f}")
            print(f"  - Change: {step_metrics.visual.change_level.value}")
        
        print(f"\nState Hash Metrics:")
        print(f"  - State Hash: {step_metrics.state_hash.state_hash[:16]}...")
        print(f"  - Perceptual Hash: {step_metrics.state_hash.perceptual_hash}")
        print(f"  - Is Duplicate: {step_metrics.state_hash.is_duplicate}")
        
        print(f"\nPerformance Metrics:")
        print(f"  - Execution Time: {step_metrics.performance.execution_time_ms:.2f}ms")
        print(f"  - Stability Wait: {step_metrics.performance.stability_wait_ms:.2f}ms")
        print(f"  - Total Time: {step_metrics.performance.total_step_time_ms:.2f}ms")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 70)


def example_custom_thresholds():
    """Example: Using custom metric thresholds"""
    print("\nEXAMPLE 4: Custom Metric Thresholds")
    print("=" * 70)
    
    temp_dir, before_path, after_path = create_sample_images()
    
    try:
        # Create custom thresholds
        custom_thresholds = MetricThresholds(
            visual_diff_no_change=0.10,      # More lenient
            visual_diff_major_change=0.40,   # Less sensitive
            loop_occurrence_threshold=5       # Require more occurrences
        )
        
        print("\nCustom Thresholds:")
        print(f"  - No Change: < {custom_thresholds.visual_diff_no_change}")
        print(f"  - Major Change: > {custom_thresholds.visual_diff_major_change}")
        print(f"  - Loop Threshold: {custom_thresholds.loop_occurrence_threshold}")
        
        # Create computer with custom thresholds
        computer = MetricComputer(thresholds=custom_thresholds, output_dir=str(temp_dir))
        
        # Compute metrics
        step_metrics = computer.compute_step_metrics(
            step_id=1,
            before_screenshot=before_path,
            after_screenshot=after_path
        )
        
        print(f"\n✓ Change Level (custom thresholds): {step_metrics.visual.change_level.value}")
        
        # Update thresholds dynamically
        new_thresholds = MetricThresholds(visual_diff_no_change=0.02)
        computer.update_thresholds(new_thresholds)
        print(f"\n✓ Thresholds updated dynamically")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 70)


def main():
    """Run all examples"""
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 16 + "METRIC COMPUTATION EXAMPLES" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run examples
    example_visual_metrics()
    example_state_hashing()
    example_step_metrics()
    example_custom_thresholds()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
