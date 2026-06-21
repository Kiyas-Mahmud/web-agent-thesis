"""
Tests for Browser Recorder module
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from browser_recorder import (
    Action, ActionType, ActionResult, Step, Trajectory,
    BrowserRecorder, SessionManager, ScreenshotCapture
)


class TestActionSchema:
    """Test action schema models"""
    
    def test_create_click_action(self):
        """Test creating a CLICK action"""
        action = Action(
            action_type=ActionType.CLICK,
            target="#submit-btn",
            description="Click submit button"
        )
        
        assert action.action_type == ActionType.CLICK
        assert action.target == "#submit-btn"
        assert action.description == "Click submit button"
        assert action.timeout == 30000  # Default
    
    def test_create_type_action(self):
        """Test creating a TYPE action"""
        action = Action(
            action_type=ActionType.TYPE,
            target="#username",
            value="testuser",
            description="Enter username"
        )
        
        assert action.action_type == ActionType.TYPE
        assert action.target == "#username"
        assert action.value == "testuser"
    
    def test_create_navigate_action(self):
        """Test creating a NAVIGATE action"""
        action = Action(
            action_type=ActionType.NAVIGATE,
            value="https://example.com",
            description="Navigate to homepage"
        )
        
        assert action.action_type == ActionType.NAVIGATE
        assert action.value == "https://example.com"
    
    def test_action_to_dict(self):
        """Test converting action to dictionary"""
        action = Action(
            action_type=ActionType.CLICK,
            target="#btn",
            description="Click button"
        )
        
        action_dict = action.to_dict()
        
        assert action_dict['action_type'] == 'click'
        assert action_dict['target'] == "#btn"
        assert 'timestamp' in action_dict
    
    def test_action_result(self):
        """Test action result creation"""
        result = ActionResult(
            success=True,
            execution_time_ms=150.5,
            element_found=True,
            final_url="https://example.com/page"
        )
        
        assert result.success is True
        assert result.execution_time_ms == 150.5
        assert result.element_found is True
        assert result.error is None
    
    def test_action_result_with_error(self):
        """Test action result with error"""
        result = ActionResult(
            success=False,
            error="Element not found: #missing-element",
            execution_time_ms=100.0,
            element_found=False
        )
        
        assert result.success is False
        assert "Element not found" in result.error


class TestStep:
    """Test Step model"""
    
    def test_create_step(self):
        """Test creating a step"""
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
        
        assert step.step_id == 1
        assert step.action.action_type == ActionType.CLICK
        assert step.result.success is True
        assert step.screenshot_before == "before_0001.png"
    
    def test_step_to_dict(self):
        """Test converting step to dictionary"""
        action = Action(action_type=ActionType.CLICK, target="#btn")
        result = ActionResult(success=True, execution_time_ms=100.0)
        
        step = Step(
            step_id=1,
            action=action,
            result=result,
            screenshot_before="before.png",
            screenshot_after="after.png"
        )
        
        step_dict = step.to_dict()
        
        assert step_dict['step_id'] == 1
        assert 'action' in step_dict
        assert 'result' in step_dict
        assert 'timestamp' in step_dict


class TestTrajectory:
    """Test Trajectory model"""
    
    def test_create_trajectory(self):
        """Test creating a trajectory"""
        trajectory = Trajectory(
            task_id="task_001",
            start_url="https://example.com"
        )
        
        assert trajectory.task_id == "task_001"
        assert trajectory.start_url == "https://example.com"
        assert trajectory.steps == []
        assert trajectory.success is None
    
    def test_add_steps(self):
        """Test adding steps to trajectory"""
        trajectory = Trajectory(
            task_id="task_001",
            start_url="https://example.com"
        )
        
        # Add first step
        action1 = Action(action_type=ActionType.CLICK, target="#btn1")
        result1 = ActionResult(success=True, execution_time_ms=100.0)
        step1 = Step(step_id=1, action=action1, result=result1)
        
        trajectory.add_step(step1)
        assert trajectory.get_step_count() == 1
        
        # Add second step
        action2 = Action(action_type=ActionType.TYPE, target="#input", value="test")
        result2 = ActionResult(success=True, execution_time_ms=150.0)
        step2 = Step(step_id=2, action=action2, result=result2)
        
        trajectory.add_step(step2)
        assert trajectory.get_step_count() == 2
    
    def test_trajectory_statistics(self):
        """Test trajectory statistics"""
        trajectory = Trajectory(
            task_id="task_001",
            start_url="https://example.com"
        )
        
        # Add successful step
        action1 = Action(action_type=ActionType.CLICK, target="#btn")
        result1 = ActionResult(success=True, execution_time_ms=100.0)
        step1 = Step(step_id=1, action=action1, result=result1)
        trajectory.add_step(step1)
        
        # Add failed step
        action2 = Action(action_type=ActionType.CLICK, target="#missing")
        result2 = ActionResult(success=False, execution_time_ms=50.0, error="Not found")
        step2 = Step(step_id=2, action=action2, result=result2)
        trajectory.add_step(step2)
        
        assert trajectory.get_step_count() == 2
    
    def test_trajectory_to_dict(self):
        """Test converting trajectory to dictionary"""
        trajectory = Trajectory(
            task_id="task_001",
            start_url="https://example.com"
        )
        
        trajectory_dict = trajectory.to_dict()
        
        assert trajectory_dict['task_id'] == "task_001"
        assert trajectory_dict['start_url'] == "https://example.com"
        assert 'start_time' in trajectory_dict
        assert 'steps' in trajectory_dict


class TestBrowserRecorder:
    """Test BrowserRecorder class (basic tests without actual browser)"""
    
    def test_create_browser_recorder(self):
        """Test creating a BrowserRecorder instance"""
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
        
        assert recorder.session_manager is not None
        assert recorder.screenshot_capture is not None
        assert recorder.current_trajectory is None
        assert recorder.current_step_id == 0
    
    def test_get_statistics_no_trajectory(self):
        """Test getting statistics when no trajectory exists"""
        recorder = BrowserRecorder()
        stats = recorder.get_statistics()
        
        assert stats == {}
    
    def test_action_validation(self):
        """Test that actions are validated properly"""
        # Valid click action
        action = Action(
            action_type=ActionType.CLICK,
            target="#btn"
        )
        assert action.target == "#btn"
        
        # Valid type action
        action = Action(
            action_type=ActionType.TYPE,
            target="#input",
            value="test"
        )
        assert action.value == "test"


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("BROWSER RECORDER TESTS")
    print("=" * 70)
    
    results = {
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    test_classes = [
        TestActionSchema,
        TestStep,
        TestTrajectory,
        TestBrowserRecorder
    ]
    
    for test_class in test_classes:
        print(f"\n{'='*70}")
        print(f"Running: {test_class.__name__}")
        print('='*70)
        
        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                method = getattr(instance, method_name)
                method()
                results['passed'] += 1
                print(f"✓ {method_name}")
            except AssertionError as e:
                results['failed'] += 1
                results['errors'].append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"✗ {method_name}: FAILED")
                print(f"  Error: {e}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"✗ {method_name}: ERROR")
                print(f"  Error: {e}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total:  {results['passed'] + results['failed']}")
    
    if results['failed'] > 0:
        print("\nFailed Tests:")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\n🎉 All tests passed!")
    
    print("=" * 70)
    
    return results['failed'] == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
