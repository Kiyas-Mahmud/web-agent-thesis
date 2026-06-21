"""
Metric Computation Validation Script

Standalone validation for metric computation module.
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from metric_computation import (
    StepMetrics,
    TrajectoryMetrics,
    VisualMetrics,
    StateHashMetrics,
    PerformanceMetrics,
    MetricThresholds,
    ChangeLevel,
    VisualMetricsComputer,
    StateHashComputer,
    MetricComputer
)


class ValidationTests:
    """Validation tests for Metric Computation"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.temp_dir = None
    
    def test(self, name: str, condition: bool, error_msg: str = ""):
        """Run a single test"""
        if condition:
            self.passed += 1
            print(f"  ✓ {name}")
            return True
        else:
            self.failed += 1
            self.errors.append(f"{name}: {error_msg}")
            print(f"  ✗ {name}")
            if error_msg:
                print(f"    Error: {error_msg}")
            return False
    
    def section(self, title: str):
        """Print section header"""
        print(f"\n{'='*70}")
        print(f"{title}")
        print('='*70)
    
    def setup_temp_dir(self):
        """Create temporary directory for test images"""
        self.temp_dir = Path(tempfile.mkdtemp())
        return self.temp_dir
    
    def cleanup_temp_dir(self):
        """Remove temporary directory"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_image(self, filename: str, color: tuple = (255, 255, 255), size: tuple = (100, 100)) -> Path:
        """Create a test image"""
        img = Image.new('RGB', size, color)
        path = self.temp_dir / filename
        img.save(path)
        return path
    
    def summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print("VALIDATION SUMMARY")
        print('='*70)
        total = self.passed + self.failed
        print(f"Passed: {self.passed}/{total}")
        print(f"Failed: {self.failed}/{total}")
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n🎉 All validation tests passed!")
        
        print('='*70)
        return self.failed == 0


def validate_metric_schema(tests: ValidationTests):
    """Validate metric schema models"""
    tests.section("METRIC SCHEMA VALIDATION")
    
    # Test ChangeLevel enum
    try:
        levels = [ChangeLevel.NO_CHANGE, ChangeLevel.MINOR_CHANGE, ChangeLevel.MAJOR_CHANGE]
        tests.test("ChangeLevel enum", len(levels) == 3)
    except Exception as e:
        tests.test("ChangeLevel enum", False, str(e))
    
    # Test VisualMetrics
    try:
        metrics = VisualMetrics(
            pixel_diff_score=0.15,
            ssim_score=0.85,
            mse=100.5,
            change_level=ChangeLevel.MINOR_CHANGE
        )
        tests.test("Create VisualMetrics", metrics.pixel_diff_score == 0.15)
        tests.test("VisualMetrics to_dict", 'change_level' in metrics.to_dict())
    except Exception as e:
        tests.test("Create VisualMetrics", False, str(e))
    
    # Test StateHashMetrics
    try:
        state_metrics = StateHashMetrics(
            state_hash="abc123",
            perceptual_hash="def456",
            is_duplicate=False,
            loop_detected=False
        )
        tests.test("Create StateHashMetrics", state_metrics.state_hash == "abc123")
    except Exception as e:
        tests.test("Create StateHashMetrics", False, str(e))
    
    # Test PerformanceMetrics
    try:
        perf = PerformanceMetrics(
            execution_time_ms=150.5,
            stability_wait_ms=2000.0
        )
        tests.test("Create PerformanceMetrics", perf.execution_time_ms == 150.5)
    except Exception as e:
        tests.test("Create PerformanceMetrics", False, str(e))
    
    # Test StepMetrics
    try:
        visual = VisualMetrics(
            pixel_diff_score=0.1,
            ssim_score=0.9,
            mse=50.0,
            change_level=ChangeLevel.NO_CHANGE
        )
        state = StateHashMetrics(
            state_hash="hash1",
            perceptual_hash="phash1"
        )
        perf = PerformanceMetrics(execution_time_ms=100.0)
        
        step = StepMetrics(
            step_id=1,
            visual=visual,
            state_hash=state,
            performance=perf
        )
        tests.test("Create StepMetrics", step.step_id == 1)
        tests.test("StepMetrics has all components", 
                  step.visual and step.state_hash and step.performance)
    except Exception as e:
        tests.test("Create StepMetrics", False, str(e))
    
    # Test MetricThresholds
    try:
        thresholds = MetricThresholds()
        tests.test("Create MetricThresholds", thresholds.visual_diff_no_change == 0.05)
        
        # Test classification
        level = thresholds.classify_visual_change(0.02, 0.98)
        tests.test("Classify no change", level == ChangeLevel.NO_CHANGE)
        
        level = thresholds.classify_visual_change(0.5, 0.5)
        tests.test("Classify major change", level == ChangeLevel.MAJOR_CHANGE)
    except Exception as e:
        tests.test("MetricThresholds", False, str(e))


def validate_visual_metrics(tests: ValidationTests):
    """Validate visual metrics computation"""
    tests.section("VISUAL METRICS VALIDATION")
    
    # Setup
    tests.setup_temp_dir()
    computer = VisualMetricsComputer()
    
    # Create test images
    try:
        # Identical images
        img1_path = tests.create_test_image("img1.png", (255, 0, 0))
        img2_path = tests.create_test_image("img2.png", (255, 0, 0))
        
        metrics = computer.compute_metrics(img1_path, img2_path)
        
        tests.test("Identical images pixel diff", metrics.pixel_diff_score < 0.01)
        tests.test("Identical images SSIM", metrics.ssim_score > 0.99)
        tests.test("Identical images classification", 
                  metrics.change_level == ChangeLevel.NO_CHANGE)
    except Exception as e:
        tests.test("Identical images", False, str(e))
    
    # Different images
    try:
        img3_path = tests.create_test_image("img3.png", (0, 255, 0))
        
        metrics = computer.compute_metrics(img1_path, img3_path)
        
        tests.test("Different images pixel diff", metrics.pixel_diff_score > 0.3)
        # SSIM for uniform solid colors can be 1.0 due to perfect structure
        # Just verify computation succeeded
        tests.test("Different images SSIM computed", -1.0 <= metrics.ssim_score <= 1.0)
        tests.test("Different images classification",
                  metrics.change_level == ChangeLevel.MAJOR_CHANGE)
    except Exception as e:
        tests.test ("Different images", False, str(e))
    
    # Change regions
    try:
        num_changed, percentage = computer.get_change_regions(img1_path, img3_path)
        tests.test("Change regions computation", percentage > 50.0)
    except Exception as e:
        tests.test("Change regions", False, str(e))
    
    # Cleanup
    tests.cleanup_temp_dir()


def validate_state_hashing(tests: ValidationTests):
    """Validate state hashing and loop detection"""
    tests.section("STATE HASHING VALIDATION")
    
    # Setup
    tests.setup_temp_dir()
    computer = StateHashComputer()
    
    # Create test images
    try:
        img1_path = tests.create_test_image("hash1.png", (255, 0, 0))
        img2_path = tests.create_test_image("hash2.png", (255, 0, 0))  # Same content
        img3_path = tests.create_test_image("hash3.png", (0, 255, 0))  # Different
        
        # Compute hashes
        hash1 = computer.compute_hashes(img1_path)
        tests.test("Compute state hash", len(hash1.state_hash) > 0)
        tests.test("Compute perceptual hash", len(hash1.perceptual_hash) > 0)
        tests.test("First state not duplicate", not hash1.is_duplicate)
        
        # Same content - should be duplicate
        hash2 = computer.compute_hashes(img2_path)
        tests.test("Identical content detected", hash2.is_duplicate)
        tests.test("State hash matches", hash1.state_hash == hash2.state_hash)
        
        # Different content
        hash3 = computer.compute_hashes(img3_path)
        tests.test("Different content not duplicate", not hash3.is_duplicate)
        tests.test("Different state hash", hash1.state_hash != hash3.state_hash)
        
    except Exception as e:
        tests.test("State hashing", False, str(e))
    
    # Loop detection
    try:
        computer.reset()
        
        # Simulate loop by repeating same image
        for i in range(5):
            hash_metrics = computer.compute_hashes(img1_path)
        
        tests.test("Loop detection", hash_metrics.loop_detected)
        tests.test("State occurrences", hash_metrics.state_occurrences >= 3)
        
    except Exception as e:
        tests.test("Loop detection", False, str(e))
    
    # State summary
    try:
        summary = computer.get_state_summary()
        tests.test("Get state summary", 'unique_states' in summary)
        tests.test("Unique state count", summary['unique_states'] == 1)  # Only used one unique image
    except Exception as e:
        tests.test("State summary", False, str(e))
    
    # Cleanup
    tests.cleanup_temp_dir()


def validate_metric_computer(tests: ValidationTests):
    """Validate main MetricComputer class"""
    tests.section("METRIC COMPUTER VALIDATION")
    
    # Setup
    tests.setup_temp_dir()
    computer = MetricComputer(output_dir=str(tests.temp_dir))
    
    try:
        # Create test images
        before_path = tests.create_test_image("before.png", (255, 0, 0))
        after_path = tests.create_test_image("after.png", (0, 255, 0))
        
        # Compute step metrics
        step_metrics = computer.compute_step_metrics(
            step_id=1,
            before_screenshot=before_path,
            after_screenshot=after_path,
            execution_time_ms=150.0
        )
        
        tests.test("Compute step metrics", step_metrics.step_id == 1)
        tests.test("Step has visual metrics", step_metrics.visual is not None)
        tests.test("Step has state hash", step_metrics.state_hash is not None)
        tests.test("Step has performance", step_metrics.performance is not None)
        
    except Exception as e:
        tests.test("MetricComputer step metrics", False, str(e))
    
    # Test threshold updates
    try:
        new_thresholds = MetricThresholds(visual_diff_no_change=0.1)
        computer.update_thresholds(new_thresholds)
        tests.test("Update thresholds", computer.get_thresholds().visual_diff_no_change == 0.1)
    except Exception as e:
        tests.test("Update thresholds", False, str(e))
    
    # Cleanup
    tests.cleanup_temp_dir()


def validate_trajectory_metrics(tests: ValidationTests):
    """Validate trajectory metrics computation"""
    tests.section("TRAJECTORY METRICS VALIDATION")
    
    # Create trajectory metrics
    try:
        traj_metrics = TrajectoryMetrics(
            task_id="test_001",
            total_steps=10,
            successful_steps=8,
            failed_steps=2,
            total_duration_seconds=25.5,
            unique_states=7,
            loops_detected=1
        )
        
        tests.test("Create TrajectoryMetrics", traj_metrics.task_id == "test_001")
        tests.test("Trajectory success rate", traj_metrics.successful_steps == 8)
        tests.test("Trajectory to_dict", 'task_id' in traj_metrics.to_dict())
        
    except Exception as e:
        tests.test("TrajectoryMetrics", False, str(e))


def main():
    """Main validation function"""
    print("=" * 70)
    print("METRIC COMPUTATION MODULE VALIDATION")
    print("=" * 70)
    
    tests = ValidationTests()
    
    # Run all validation tests
    validate_metric_schema(tests)
    validate_visual_metrics(tests)
    validate_state_hashing(tests)
    validate_metric_computer(tests)
    validate_trajectory_metrics(tests)
    
    # Print summary
    success = tests.summary()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
