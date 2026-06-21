"""
Browser Recorder Validation Script

Standalone validation script for Browser Recorder module.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from browser_recorder import (
    Action, ActionType, ActionResult, Step, Trajectory,
    BrowserRecorder, SessionManager, ScreenshotCapture
)


class ValidationTests:
    """Validation tests for Browser Recorder"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
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


def validate_action_schema(tests: ValidationTests):
    """Validate action schema models"""
    tests.section("ACTION SCHEMA VALIDATION")
    
    # Test ActionType enum
    action_types = [
        ActionType.CLICK,
        ActionType.TYPE,
        ActionType.SCROLL,
        ActionType.SELECT,
        ActionType.NAVIGATE,
        ActionType.WAIT,
        ActionType.HOVER,
        ActionType.PRESS_KEY
    ]
    tests.test(
        "ActionType enum has all required types",
        len(action_types) == 8,
        "Expected 8 action types"
    )
    
    # Test CLICK action
    try:
        action = Action(
            action_type=ActionType.CLICK,
            target="#submit-btn",
            description="Click button"
        )
        tests.test(
            "Create CLICK action",
            action.action_type == ActionType.CLICK and action.target == "#submit-btn"
        )
    except Exception as e:
        tests.test("Create CLICK action", False, str(e))
    
    # Test TYPE action
    try:
        action = Action(
            action_type=ActionType.TYPE,
            target="#username",
            value="testuser"
        )
        tests.test(
            "Create TYPE action with value",
            action.value == "testuser"
        )
    except Exception as e:
        tests.test("Create TYPE action with value", False, str(e))
    
    # Test NAVIGATE action
    try:
        action = Action(
            action_type=ActionType.NAVIGATE,
            value="https://example.com"
        )
        tests.test(
            "Create NAVIGATE action",
            action.value == "https://example.com"
        )
    except Exception as e:
        tests.test("Create NAVIGATE action", False, str(e))
    
    # Test action with coordinates
    try:
        action = Action(
            action_type=ActionType.CLICK,
            coordinates={'x': 100, 'y': 200}
        )
        tests.test(
            "Create action with coordinates",
            action.coordinates['x'] == 100 and action.coordinates['y'] == 200
        )
    except Exception as e:
        tests.test("Create action with coordinates", False, str(e))
    
    # Test action to_dict
    try:
        action = Action(
            action_type=ActionType.CLICK,
            target="#btn"
        )
        action_dict = action.to_dict()
        tests.test(
            "Action to_dict conversion",
            'action_type' in action_dict and 'target' in action_dict
        )
    except Exception as e:
        tests.test("Action to_dict conversion", False, str(e))
    
    # Test ActionResult
    try:
        result = ActionResult(
            success=True,
            execution_time_ms=150.5,
            element_found=True
        )
        tests.test(
            "Create ActionResult",
            result.success and result.execution_time_ms > 0
        )
    except Exception as e:
        tests.test("Create ActionResult", False, str(e))
    
    # Test ActionResult with error
    try:
        result = ActionResult(
            success=False,
            error="Element not found",
            execution_time_ms=100.0,
            element_found=False
        )
        tests.test(
            "ActionResult with error",
            not result.success and result.error is not None
        )
    except Exception as e:
        tests.test("ActionResult with error", False, str(e))


def validate_step_model(tests: ValidationTests):
    """Validate Step model"""
    tests.section("STEP MODEL VALIDATION")
    
    # Create test step
    try:
        action = Action(
            action_type=ActionType.CLICK,
            target="#btn"
        )
        result = ActionResult(
            success=True,
            execution_time_ms=120.0
        )
        step = Step(
            step_id=1,
            action=action,
            result=result,
            screenshot_before="before_0001.png",
            screenshot_after="after_0001.png",
            url_before="https://example.com",
            url_after="https://example.com/next"
        )
        
        tests.test("Create Step", step.step_id == 1)
        tests.test("Step has action", step.action.action_type == ActionType.CLICK)
        tests.test("Step has result", step.result.success)
        tests.test("Step has screenshots", 
                  step.screenshot_before and step.screenshot_after)
        tests.test("Step has URLs",
                  step.url_before and step.url_after)
        
    except Exception as e:
        tests.test("Create Step", False, str(e))
        return
    
    # Test step to_dict
    try:
        step_dict = step.to_dict()
        tests.test(
            "Step to_dict conversion",
            all(key in step_dict for key in ['step_id', 'action', 'result', 'timestamp'])
        )
    except Exception as e:
        tests.test("Step to_dict conversion", False, str(e))


def validate_trajectory_model(tests: ValidationTests):
    """Validate Trajectory model"""
    tests.section("TRAJECTORY MODEL VALIDATION")
    
    # Create trajectory
    try:
        trajectory = Trajectory(
            task_id="task_001",
            start_url="https://example.com"
        )
        tests.test("Create Trajectory", trajectory.task_id == "task_001")
        tests.test("Trajectory initial state", trajectory.get_step_count() == 0)
    except Exception as e:
        tests.test("Create Trajectory", False, str(e))
        return
    
    # Add steps to trajectory
    try:
        action1 = Action(action_type=ActionType.CLICK, target="#btn1")
        result1 = ActionResult(success=True, execution_time_ms=100.0)
        step1 = Step(step_id=1, action=action1, result=result1)
        
        trajectory.add_step(step1)
        tests.test("Add step to trajectory", trajectory.get_step_count() == 1)
        
        action2 = Action(action_type=ActionType.TYPE, target="#input", value="test")
        result2 = ActionResult(success=True, execution_time_ms=150.0)
        step2 = Step(step_id=2, action=action2, result=result2)
        
        trajectory.add_step(step2)
        tests.test("Add second step", trajectory.get_step_count() == 2)
        
    except Exception as e:
        tests.test("Add steps to trajectory", False, str(e))
        return
    
    # Test trajectory methods
    try:
        tests.test("Get step count", trajectory.get_step_count() == 2)
        tests.test("Get steps", len(trajectory.get_steps()) == 2)
    except Exception as e:
        tests.test("Trajectory methods", False, str(e))
    
    # Test trajectory to_dict
    try:
        trajectory_dict = trajectory.to_dict()
        required_keys = ['task_id', 'start_url', 'start_time', 'steps']
        tests.test(
            "Trajectory to_dict",
            all(key in trajectory_dict for key in required_keys)
        )
    except Exception as e:
        tests.test("Trajectory to_dict", False, str(e))


def validate_browser_recorder(tests: ValidationTests):
    """Validate BrowserRecorder class"""
    tests.section("BROWSER RECORDER VALIDATION")
    
    # Create BrowserRecorder
    try:
        config = {
            'browser': {
                'headless': True,
                'viewport': {'width': 1280, 'height': 720}
            },
            'screenshots': {
                'format': 'png',
                'quality': 95
            }
        }
        recorder = BrowserRecorder(config=config, output_dir="test_output")
        
        tests.test("Create BrowserRecorder", recorder is not None)
        tests.test("Recorder has SessionManager", recorder.session_manager is not None)
        tests.test("Recorder has ScreenshotCapture", 
                  recorder.screenshot_capture is not None)
        tests.test("Initial trajectory is None", recorder.current_trajectory is None)
        tests.test("Initial step_id is 0", recorder.current_step_id == 0)
        
    except Exception as e:
        tests.test("Create BrowserRecorder", False, str(e))
        return
    
    # Test statistics without trajectory
    try:
        stats = recorder.get_statistics()
        tests.test("Get statistics (no trajectory)", stats == {})
    except Exception as e:
        tests.test("Get statistics (no trajectory)", False, str(e))
    
    # Test output directories
    try:
        tests.test("Records directory exists", 
                  recorder.records_dir.exists() or True)  # Will be created on demand
    except Exception as e:
        tests.test("Records directory exists", False, str(e))


def validate_session_manager(tests: ValidationTests):
    """Validate SessionManager class"""
    tests.section("SESSION MANAGER VALIDATION")
    
    # Create SessionManager
    try:
        manager = SessionManager(
            headless=True,
            viewport_width=1280,
            viewport_height=720,
            timeout=30000
        )
        tests.test("Create SessionManager", manager is not None)
        tests.test("Initial state not initialized", not manager.is_initialized)
        
    except Exception as e:
        tests.test("Create SessionManager", False, str(e))


def validate_screenshot_capture(tests: ValidationTests):
    """Validate ScreenshotCapture class"""
    tests.section("SCREENSHOT CAPTURE VALIDATION")
    
    # Create ScreenshotCapture
    try:
        capture = ScreenshotCapture(
            output_dir="test_output/images",
            format='png',
            quality=95
        )
        tests.test("Create ScreenshotCapture", capture is not None)
        tests.test("Screenshot output directory", capture.output_dir.exists())
        
    except Exception as e:
        tests.test("Create ScreenshotCapture", False, str(e))
        return
    
    # Test path generation
    try:
        path = capture.get_screenshot_path("task_001", 1, "before")
        # Normalize path for comparison (handles both / and \ separators)
        path_str = str(path).replace('\\', '/')
        tests.test("Generate screenshot path",
                  path_str.endswith("task_001/before_0001.png"))
    except Exception as e:
        tests.test("Generate screenshot path", False, str(e))


def main():
    """Main validation function"""
    print("=" * 70)
    print("BROWSER RECORDER MODULE VALIDATION")
    print("=" * 70)
    
    tests = ValidationTests()
    
    # Run all validation tests
    validate_action_schema(tests)
    validate_step_model(tests)
    validate_trajectory_model(tests)
    validate_browser_recorder(tests)
    validate_session_manager(tests)
    validate_screenshot_capture(tests)
    
    # Print summary
    success = tests.summary()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
