"""
Example: Using Browser Recorder

Demonstrates how to use the BrowserRecorder to record web interactions.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from browser_recorder import BrowserRecorder, Action, ActionType


async def example_basic_recording():
    """Basic example: Record a simple web interaction"""
    
    print("=" * 70)
    print("EXAMPLE 1: Basic Recording")
    print("=" * 70)
    
    # Configure recorder
    config = {
        'browser': {
            'headless': True,  # Run without visible browser
            'viewport': {'width': 1280, 'height': 720},
            'timeout': 30000  # 30 seconds
        },
        'screenshots': {
            'format': 'png',
            'quality': 95
        }
    }
    
    # Create recorder
    recorder = BrowserRecorder(config=config, output_dir="examples/output")
    
    try:
        # Start recording session
        print("\n1. Starting session...")
        await recorder.start_session(
            task_id="example_001",
            start_url="https://example.com"
        )
        
        # Record some actions
        print("2. Recording navigation...")
        step1 = await recorder.record_step(
            Action(
                action_type=ActionType.NAVIGATE,
                value="https://www.wikipedia.org",
                description="Navigate to Wikipedia"
            )
        )
        print(f"   Step {step1.step_id}: {step1.result.success}")
        
        print("3. Recording scroll...")
        step2 = await recorder.record_step(
            Action(
                action_type=ActionType.SCROLL,
                scroll_amount=500,
                description="Scroll down page"
            )
        )
        print(f"   Step {step2.step_id}: {step2.result.success}")
        
        # Get statistics
        stats = recorder.get_statistics()
        print("\n4. Statistics:")
        print(f"   Task ID: {stats['task_id']}")
        print(f"   Total steps: {stats['total_steps']}")
        print(f"   Successful: {stats['successful_steps']}")
        print(f"   Failed: {stats['failed_steps']}")
        
        # End session successfully
        print("\n5. Ending session...")
        await recorder.end_session(success=True)
        
        print("\n✓ Recording completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        await recorder.end_session(success=False, error=str(e))


async def example_form_interaction():
    """Example: Record form filling interactions"""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Form Interaction Recording")
    print("=" * 70)
    
    config = {
        'browser': {'headless': True},
        'screenshots': {'format': 'png'}
    }
    
    recorder = BrowserRecorder(config=config, output_dir="examples/output")
    
    try:
        print("\n1. Starting session...")
        await recorder.start_session(
            task_id="example_002",
            start_url="https://example.com"
        )
        
        # Simulate form interactions
        actions = [
            Action(
                action_type=ActionType.CLICK,
                target="#search-btn",
                description="Click search button"
            ),
            Action(
                action_type=ActionType.TYPE,
                target="#search-input",
                value="test query",
                description="Type search query"
            ),
            Action(
                action_type=ActionType.PRESS_KEY,
                key="Enter",
                description="Press Enter to search"
            ),
            Action(
                action_type=ActionType.WAIT,
                timeout=2000,
                description="Wait for results"
            )
        ]
        
        print("\n2. Recording form interactions...")
        for action in actions:
            step = await recorder.record_step(action)
            status = "✓" if step.result.success else "✗"
            print(f"   {status} {action.description}")
        
        # Show trajectory info
        trajectory = recorder.get_trajectory()
        print(f"\n3. Trajectory info:")
        print(f"   Task: {trajectory.task_id}")
        print(f"   Steps: {trajectory.get_step_count()}")
        print(f"   Duration: {trajectory.get_duration():.2f}s")
        
        await recorder.end_session(success=True)
        print("\n✓ Form interaction recorded!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        await recorder.end_session(success=False, error=str(e))


async def example_error_handling():
    """Example: Handle action failures"""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Error Handling")
    print("=" * 70)
    
    recorder = BrowserRecorder(output_dir="examples/output")
    
    try:
        print("\n1. Starting session...")
        await recorder.start_session(
            task_id="example_003",
            start_url="https://example.com"
        )
        
        # Try an action that might fail
        print("\n2. Attempting action on non-existent element...")
        step = await recorder.record_step(
            Action(
                action_type=ActionType.CLICK,
                target="#non-existent-element",
                description="Click missing element"
            )
        )
        
        # Check result
        if step.result.success:
            print("   ✓ Action succeeded")
        else:
            print(f"   ✗ Action failed: {step.result.error}")
            print(f"   Element found: {step.result.element_found}")
        
        # Continue with valid action
        print("\n3. Performing valid action...")
        step2 = await recorder.record_step(
            Action(
                action_type=ActionType.WAIT,
                timeout=1000,
                description="Wait"
            )
        )
        print(f"   ✓ Valid action: {step2.result.success}")
        
        # End with partial success
        stats = recorder.get_statistics()
        has_failures = stats['failed_steps'] > 0
        
        print(f"\n4. Final stats:")
        print(f"   Successful: {stats['successful_steps']}")
        print(f"   Failed: {stats['failed_steps']}")
        
        await recorder.end_session(
            success=not has_failures,
            error="Some actions failed" if has_failures else None
        )
        
        print("\n✓ Error handling example completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        await recorder.end_session(success=False, error=str(e))


async def main():
    """Run all examples"""
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "BROWSER RECORDER EXAMPLES" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run examples
    await example_basic_recording()
    
    # Uncomment to run additional examples
    # await example_form_interaction()
    # await example_error_handling()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    # Run async examples
    asyncio.run(main())
