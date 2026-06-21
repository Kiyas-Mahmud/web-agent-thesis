"""
Browser Recorder

Main class for recording browser interactions and building trajectories.
"""

from typing import Optional, Dict, Any, List
import logging
import time
import json
from pathlib import Path

from .action_schema import Action, ActionType, ActionResult, Step, Trajectory
from .session_manager import SessionManager
from .screenshot_capture import ScreenshotCapture

logger = logging.getLogger(__name__)


class BrowserRecorder:
    """
    Main class for recording browser interactions.
    Handles action execution, screenshot capture, and trajectory building.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        output_dir: str = "dataset"
    ):
        """
        Initialize BrowserRecorder.
        
        Args:
            config: Configuration dictionary
            output_dir: Base directory for output
        """
        config = config or {}
        
        # Initialize components
        browser_config = config.get('browser', {})
        self.session_manager = SessionManager(
            headless=browser_config.get('headless', True),
            viewport_width=browser_config.get('viewport', {}).get('width', 1280),
            viewport_height=browser_config.get('viewport', {}).get('height', 720),
            timeout=browser_config.get('timeout', 30000)
        )
        
        screenshot_config = config.get('screenshots', {})
        self.screenshot_capture = ScreenshotCapture(
            output_dir=f"{output_dir}/images",
            format=screenshot_config.get('format', 'png'),
            quality=screenshot_config.get('quality', 95)
        )
        
        # Output paths
        self.output_dir = Path(output_dir)
        self.records_dir = self.output_dir / "records"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        
        # Current trajectory
        self.current_trajectory: Optional[Trajectory] = None
        self.current_step_id = 0
        
        logger.info("BrowserRecorder initialized")
    
    async def start_session(self, task_id: str, start_url: str) -> bool:
        """
        Start a new recording session for a task.
        
        Args:
            task_id: Task identifier
            start_url: Initial URL
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Starting session for task: {task_id}")
            
            # Initialize browser
            await self.session_manager.initialize()
            await self.session_manager.create_context()
            await self.session_manager.create_page(start_url)
            
            # Initialize trajectory
            self.current_trajectory = Trajectory(
                task_id=task_id,
                start_url=start_url
            )
            self.current_step_id = 0
            
            # Wait for page to stabilize
            await self.session_manager.wait_for_stability()
            
            logger.info(f"Session started successfully for task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False
    
    async def execute_action(self, action: Action) -> ActionResult:
        """
        Execute a browser action.
        
        Args:
            action: Action to execute
        
        Returns:
            ActionResult with execution details
        """
        if not self.session_manager.page:
            raise RuntimeError("No active page. Call start_session() first.")
        
        page = self.session_manager.page
        start_time = time.time()
        
        try:
            # Execute based on action type
            page_health = None
            
            if action.action_type == ActionType.CLICK:
                success = await self._execute_click(page, action)
            
            elif action.action_type == ActionType.TYPE:
                success = await self._execute_type(page, action)
            
            elif action.action_type == ActionType.SCROLL:
                success = await self._execute_scroll(page, action)
            
            elif action.action_type == ActionType.SELECT:
                success = await self._execute_select(page, action)
            
            elif action.action_type == ActionType.NAVIGATE:
                nav_result = await self._execute_navigate(page, action)
                success = nav_result["success"]
                page_health = nav_result
            
            elif action.action_type == ActionType.WAIT:
                success = await self._execute_wait(page, action)
            
            elif action.action_type == ActionType.HOVER:
                success = await self._execute_hover(page, action)
            
            elif action.action_type == ActionType.PRESS_KEY:
                success = await self._execute_press_key(page, action)
            
            else:
                raise ValueError(f"Unknown action type: {action.action_type}")
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get page info
            page_info = await self.session_manager.get_page_info()
            
            # Build result
            result_data = {
                "success": success,
                "execution_time_ms": execution_time,
                "element_found": success,
                "final_url": page_info.get('url'),
                "page_title": page_info.get('title')
            }
            
            # Add page health info if available (for NAVIGATE actions)
            if page_health:
                result_data.update({
                    "page_status": page_health.get("page_status"),
                    "http_status": page_health.get("http_status"),
                    "dom_ready_state": page_health.get("dom_ready_state"),
                    "navigation_error": page_health.get("navigation_error"),
                    "is_error_page": page_health.get("is_error_page")
                })
            
            return ActionResult(**result_data)
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Action execution failed: {e}")
            
            return ActionResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                element_found=False
            )
    
    async def _execute_click(self, page, action: Action) -> bool:
        """Execute CLICK action"""
        try:
            if action.coordinates:
                # Click at coordinates
                await page.mouse.click(
                    action.coordinates['x'],
                    action.coordinates['y']
                )
            elif action.target:
                # Click element by selector
                await page.click(action.target, timeout=action.timeout)
            else:
                raise ValueError("CLICK action requires either target or coordinates")
            
            logger.debug(f"Clicked: {action.target or action.coordinates}")
            return True
        except Exception as e:
            logger.warning(f"Click failed: {e}")
            return False
    
    async def _execute_type(self, page, action: Action) -> bool:
        """Execute TYPE action"""
        try:
            if not action.target or not action.value:
                raise ValueError("TYPE action requires target and value")
            
            timeout = action.timeout or 30000
            # Clear existing content first
            await page.fill(action.target, "", timeout=timeout)
            # Type new content
            await page.type(action.target, action.value, delay=50, timeout=timeout)
            
            logger.debug(f"Typed in {action.target}: {action.value}")
            return True
        except Exception as e:
            logger.warning(f"Type failed: {e}")
            return False
    
    async def _execute_scroll(self, page, action: Action) -> bool:
        """Execute SCROLL action"""
        try:
            scroll_amount = action.scroll_amount or 500
            timeout = action.timeout or 30000
            
            if action.target:
                # Scroll element into view
                await page.locator(action.target).scroll_into_view_if_needed(timeout=timeout)
            else:
                # Scroll page
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            
            logger.debug(f"Scrolled: {scroll_amount}px")
            return True
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
            return False
    
    async def _execute_select(self, page, action: Action) -> bool:
        """Execute SELECT action"""
        try:
            if not action.target or not action.value:
                raise ValueError("SELECT action requires target and value")
            
            await page.select_option(action.target, value=action.value, timeout=action.timeout or 30000)
            
            logger.debug(f"Selected {action.value} in {action.target}")
            return True
        except Exception as e:
            logger.warning(f"Select failed: {e}")
            return False
    
    async def _execute_navigate(self, page, action: Action) -> Dict[str, Any]:
        """
        Execute NAVIGATE action with comprehensive page status detection.
        
        Returns:
            Dict with navigation result and page health status
        """
        try:
            if not action.value:
                raise ValueError("NAVIGATE action requires value (URL)")
            
            nav_result = await self.session_manager.navigate_to(action.value)
            
            # Apply stricter success criteria
            success = (
                nav_result["page_status"] == "LOADED" and
                not nav_result["is_error_page"] and
                nav_result["http_status"] in [None, 200, 201, 301, 302, 304]  # None for non-HTTP schemes
            )
            
            nav_result["success"] = success
            
            logger.debug(f"Navigated to: {action.value} (status: {nav_result['page_status']})")
            return nav_result
            
        except Exception as e:
            logger.warning(f"Navigate failed: {e}")
            return {
                "success": False,
                "page_status": "ERROR_PAGE",
                "http_status": None,
                "dom_ready_state": "loading",
                "navigation_error": str(e),
                "is_error_page": True,
                "final_url": ""
            }
    
    async def _execute_wait(self, page, action: Action) -> bool:
        """Execute WAIT action"""
        try:
            wait_time = action.timeout or 1000
            await page.wait_for_timeout(wait_time)
            
            logger.debug(f"Waited: {wait_time}ms")
            return True
        except Exception as e:
            logger.warning(f"Wait failed: {e}")
            return False
    
    async def _execute_hover(self, page, action: Action) -> bool:
        """Execute HOVER action"""
        try:
            if not action.target:
                raise ValueError("HOVER action requires target")
            
            await page.hover(action.target, timeout=action.timeout or 30000)
            
            logger.debug(f"Hovered: {action.target}")
            return True
        except Exception as e:
            logger.warning(f"Hover failed: {e}")
            return False
    
    async def _execute_press_key(self, page, action: Action) -> bool:
        """Execute PRESS_KEY action"""
        try:
            if not action.key:
                raise ValueError("PRESS_KEY action requires key")
            
            await page.keyboard.press(action.key)
            
            logger.debug(f"Pressed key: {action.key}")
            return True
        except Exception as e:
            logger.warning(f"Press key failed: {e}")
            return False
    
    async def record_step(self, action: Action) -> Step:
        """
        Record a complete step (before screenshot, action, after screenshot).
        
        Args:
            action: Action to execute
        
        Returns:
            Completed Step object
        """
        if not self.current_trajectory:
            raise RuntimeError("No active trajectory. Call start_session() first.")
        
        page = self.session_manager.page
        task_id = self.current_trajectory.task_id
        self.current_step_id += 1
        
        # Get URL before action
        page_info_before = await self.session_manager.get_page_info()
        url_before = page_info_before.get('url')
        
        # Capture before screenshot
        screenshot_before = await self.screenshot_capture.capture_screenshot(
            page, task_id, self.current_step_id, "before"
        )
        
        # Execute action
        result = await self.execute_action(action)
        
        # Wait a bit for changes to render
        await self.session_manager.wait_for_stability(timeout=2000)
        
        # Capture after screenshot
        screenshot_after = await self.screenshot_capture.capture_screenshot(
            page, task_id, self.current_step_id, "after"
        )
        
        # Get URL after action
        page_info_after = await self.session_manager.get_page_info()
        url_after = page_info_after.get('url')
        
        # Create step
        step = Step(
            step_id=self.current_step_id,
            action=action,
            result=result,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after,
            url_before=url_before,
            url_after=url_after
        )
        
        # Add to trajectory
        self.current_trajectory.add_step(step)
        
        logger.info(f"Step {self.current_step_id} recorded: {action.action_type}")
        
        return step
    
    async def end_session(self, success: bool = True, error: Optional[str] = None):
        """
        End the current recording session.
        
        Args:
            success: Whether task completed successfully
            error: Optional error message
        """
        if not self.current_trajectory:
            logger.warning("No active trajectory to end")
            return
        
        # Update trajectory
        self.current_trajectory.end_time = time.time()
        self.current_trajectory.success = success
        self.current_trajectory.error = error
        
        if self.session_manager.page:
            page_info = await self.session_manager.get_page_info()
            self.current_trajectory.final_url = page_info.get('url')
        
        # Save trajectory
        await self.save_trajectory()
        
        # Cleanup
        await self.session_manager.cleanup()
        
        logger.info(f"Session ended for task: {self.current_trajectory.task_id}")
        
        self.current_trajectory = None
        self.current_step_id = 0
    
    async def save_trajectory(self):
        """Save the current trajectory to JSONL file"""
        if not self.current_trajectory:
            return
        
        task_id = self.current_trajectory.task_id
        output_file = self.records_dir / f"{task_id}.jsonl"
        
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                trajectory_dict = self.current_trajectory.to_dict()
                json.dump(trajectory_dict, f, ensure_ascii=False)
                f.write('\n')
            
            logger.info(f"Trajectory saved: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")
    
    def get_trajectory(self) -> Optional[Trajectory]:
        """Get the current trajectory"""
        return self.current_trajectory
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current trajectory"""
        if not self.current_trajectory:
            return {}
        
        successful_steps = sum(1 for step in self.current_trajectory.steps 
                             if step.result.success)
        
        return {
            "task_id": self.current_trajectory.task_id,
            "total_steps": self.current_trajectory.get_step_count(),
            "successful_steps": successful_steps,
            "failed_steps": self.current_trajectory.get_step_count() - successful_steps,
            "duration_seconds": self.current_trajectory.get_duration(),
            "success": self.current_trajectory.success
        }
