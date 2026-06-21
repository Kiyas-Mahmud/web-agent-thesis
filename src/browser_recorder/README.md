# Browser Recorder Module

A comprehensive browser automation and interaction recording system built with Playwright.

## Overview

The Browser Recorder module provides a complete solution for recording web interactions with before/after screenshots, handling action execution, and building trajectories for analysis.

## Features

- **8 Action Types**: Click, Type, Scroll, Select, Navigate, Wait, Hover, Press Key
- **Screenshot Capture**: Automatic before/after screenshots for every action
- **Async Support**: Full async/await integration with Playwright
- **Error Handling**: Graceful handling of failures and browser crashes
- **JSONL Export**: Trajectory data exported in append-only format
- **Context Isolation**: Each session runs in an isolated browser context

## Installation

```bash
# Install dependencies
pip install playwright pillow pydantic

# Install browser binaries
python -m playwright install chromium
```

## Quick Start

```python
import asyncio
from browser_recorder import BrowserRecorder, Action, ActionType

async def main():
    # Create recorder
    recorder = BrowserRecorder(output_dir="dataset")

    # Start session
    await recorder.start_session(
        task_id="task_001",
        start_url="https://example.com"
    )

    # Record action
    step = await recorder.record_step(
        Action(
            action_type=ActionType.CLICK,
            target="#submit-btn",
            description="Click submit button"
        )
    )

    # Check result
    if step.result.success:
        print("Action successful!")

    # End session
    await recorder.end_session(success=True)

# Run
asyncio.run(main())
```

## Action Types

### CLICK

Click an element or coordinates.

```python
# Click by selector
Action(
    action_type=ActionType.CLICK,
    target="#button-id"
)

# Click by coordinates
Action(
    action_type=ActionType.CLICK,
    coordinates={'x': 100, 'y': 200}
)
```

### TYPE

Type text into an input field.

```python
Action(
    action_type=ActionType.TYPE,
    target="#username",
    value="testuser"
)
```

### SCROLL

Scroll the page or an element.

```python
# Scroll page
Action(
    action_type=ActionType.SCROLL,
    scroll_amount=500
)

# Scroll element into view
Action(
    action_type=ActionType.SCROLL,
    target="#footer"
)
```

### SELECT

Select dropdown option.

```python
Action(
    action_type=ActionType.SELECT,
    target="#country",
    value="US"
)
```

### NAVIGATE

Navigate to a URL.

```python
Action(
    action_type=ActionType.NAVIGATE,
    value="https://example.com/page"
)
```

### WAIT

Wait for specified time.

```python
Action(
    action_type=ActionType.WAIT,
    timeout=2000  # 2 seconds
)
```

### HOVER

Hover over an element.

```python
Action(
    action_type=ActionType.HOVER,
    target="#menu-item"
)
```

### PRESS_KEY

Press keyboard key.

```python
Action(
    action_type=ActionType.PRESS_KEY,
    key="Enter"
)
```

## Configuration

```python
config = {
    'browser': {
        'headless': True,  # Run without visible browser
        'viewport': {
            'width': 1280,
            'height': 720
        },
        'timeout': 30000  # Default timeout in ms
    },
    'screenshots': {
        'format': 'png',
        'quality': 95
    }
}

recorder = BrowserRecorder(config=config, output_dir="dataset")
```

## Output Structure

```
dataset/
├── images/
│   └── task_001/
│       ├── before_0001.png
│       ├── after_0001.png
│       ├── before_0002.png
│       └── after_0002.png
└── records/
    └── task_001.jsonl
```

## Trajectory Format

Each line in the JSONL file contains a complete trajectory:

```json
{
  "task_id": "task_001",
  "start_url": "https://example.com",
  "start_time": 1708387200.0,
  "end_time": 1708387210.5,
  "success": true,
  "steps": [
    {
      "step_id": 1,
      "action": {
        "action_type": "click",
        "target": "#button",
        "timestamp": 1708387201.0
      },
      "result": {
        "success": true,
        "execution_time_ms": 120.5,
        "element_found": true
      },
      "screenshot_before": "task_001/before_0001.png",
      "screenshot_after": "task_001/after_0001.png",
      "url_before": "https://example.com",
      "url_after": "https://example.com/next"
    }
  ]
}
```

## API Reference

### BrowserRecorder

Main class for recording browser interactions.

#### Methods

- `start_session(task_id, start_url)` - Start recording session
- `record_step(action)` - Execute and record an action
- `execute_action(action)` - Execute action without screenshot
- `end_session(success, error)` - End session and save trajectory
- `get_trajectory()` - Get current trajectory
- `get_statistics()` - Get session statistics

### Action

Represents a browser action.

#### Properties

- `action_type` - Type of action (ActionType enum)
- `target` - CSS selector for element
- `value` - Value for TYPE/SELECT/NAVIGATE
- `coordinates` - {x, y} for coordinate-based clicks
- `scroll_amount` - Pixels to scroll
- `key` - Key name for PRESS_KEY
- `timeout` - Custom timeout in ms
- `description` - Human-readable description

### Step

Represents a complete interaction step.

#### Properties

- `step_id` - Step number
- `action` - Action object
- `result` - ActionResult object
- `screenshot_before` - Path to before screenshot
- `screenshot_after` - Path to after screenshot
- `url_before` - URL before action
- `url_after` - URL after action
- `timestamp` - Step timestamp

### Trajectory

Represents a complete task execution.

#### Properties

- `task_id` - Task identifier
- `start_url` - Initial URL
- `steps` - List of Step objects
- `start_time` - Start timestamp
- `end_time` - End timestamp
- `success` - Whether task succeeded
- `error` - Error message if failed
- `final_url` - Final URL

#### Methods

- `add_step(step)` - Add step to trajectory
- `get_step_count()` - Get number of steps
- `get_steps()` - Get all steps
- `get_duration()` - Get total duration in seconds

## Testing

Run validation tests:

```bash
python scripts/validate_browser_recorder.py
```

Expected output:

```
BROWSER RECORDER MODULE VALIDATION
======================================================================
ACTION SCHEMA VALIDATION
  ✓ All tests passing

VALIDATION SUMMARY
Passed: 33/33
Failed: 0/33

🎉 All validation tests passed!
```

## Examples

See `examples/browser_recorder_example.py` for complete examples:

- Basic recording
- Form interaction
- Error handling

Run examples:

```bash
python examples/browser_recorder_example.py
```

## Architecture

```
BrowserRecorder
├── SessionManager (Playwright lifecycle)
├── ScreenshotCapture (Image management)
└── Action Executors (8 action types)
```

## Error Handling

Actions may fail gracefully:

```python
step = await recorder.record_step(action)

if not step.result.success:
    print(f"Action failed: {step.result.error}")
    print(f"Element found: {step.result.element_found}")
```

## Dependencies

- `playwright>=1.58.0` - Browser automation
- `pillow>=10.0.0` - Image processing
- `pydantic>=2.0.0` - Data validation

## License

Part of the Failure-Aware Web Interaction Trajectory Dataset project.
