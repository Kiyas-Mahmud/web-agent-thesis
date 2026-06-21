"""
Screenshot Capture

Handles screenshot capture and storage for state visualization.
"""

from typing import Optional, Tuple
from pathlib import Path
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """
    Handles screenshot capture with consistent naming and storage.
    """
    
    def __init__(
        self,
        output_dir: str = "dataset/images",
        format: str = "png",
        quality: int = 95,
        viewport_size: Tuple[int, int] = (1280, 720)
    ):
        """
        Initialize ScreenshotCapture.
        
        Args:
            output_dir: Directory to save screenshots
            format: Image format (png, jpg)
            quality: Image quality (1-100)
            viewport_size: Browser viewport size (width, height)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.format = format.lower()
        self.quality = quality
        self.viewport_size = viewport_size
        
        logger.info(f"ScreenshotCapture initialized: {output_dir}")
    
    def get_screenshot_path(
        self,
        task_id: str,
        step_id: int,
        state: str = "before"
    ) -> Path:
        """
        Generate screenshot path following naming convention.
        
        Args:
            task_id: Task identifier
            step_id: Step number
            state: "before" or "after"
        
        Returns:
            Path object for the screenshot
        """
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{state}_{step_id:04d}.{self.format}"
        return task_dir / filename
    
    async def capture_screenshot(
        self,
        page,
        task_id: str,
        step_id: int,
        state: str = "before"
    ) -> str:
        """
        Capture screenshot from Playwright page.
        
        Args:
            page: Playwright page object
            task_id: Task identifier
            step_id: Step number
            state: "before" or "after"
        
        Returns:
            Path to saved screenshot
        """
        try:
            screenshot_path = self.get_screenshot_path(task_id, step_id, state)
            
            # Capture screenshot
            await page.screenshot(
                path=str(screenshot_path),
                full_page=False,  # Only visible viewport
                type=self.format
            )
            
            logger.debug(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return ""
    
    def capture_screenshot_sync(
        self,
        page,
        task_id: str,
        step_id: int,
        state: str = "before"
    ) -> str:
        """
        Synchronous version of capture_screenshot.
        
        Args:
            page: Selenium WebDriver or element
            task_id: Task identifier
            step_id: Step number
            state: "before" or "after"
        
        Returns:
            Path to saved screenshot
        """
        try:
            screenshot_path = self.get_screenshot_path(task_id, step_id, state)
            
            # Capture screenshot (works with Selenium)
            page.save_screenshot(str(screenshot_path))
            
            logger.debug(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return ""
    
    def process_screenshot(
        self,
        screenshot_path: str,
        resize: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Post-process screenshot (resize, compress, etc.)
        
        Args:
            screenshot_path: Path to screenshot
            resize: Optional (width, height) to resize to
        
        Returns:
            True if successful
        """
        try:
            img = Image.open(screenshot_path)
            
            # Resize if requested
            if resize:
                img = img.resize(resize, Image.LANCZOS)
            
            # Save with compression
            img.save(screenshot_path, self.format.upper(), quality=self.quality)
            
            logger.debug(f"Screenshot processed: {screenshot_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process screenshot: {e}")
            return False
    
    def get_task_screenshots(self, task_id: str) -> list:
        """
        Get all screenshots for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            List of screenshot paths
        """
        task_dir = self.output_dir / task_id
        if not task_dir.exists():
            return []
        
        screenshots = sorted(task_dir.glob(f"*.{self.format}"))
        return [str(p) for p in screenshots]
    
    def get_storage_size(self, task_id: Optional[str] = None) -> int:
        """
        Get total storage size in bytes.
        
        Args:
            task_id: Optional specific task, or None for all
        
        Returns:
            Total size in bytes
        """
        if task_id:
            task_dir = self.output_dir / task_id
            path = task_dir if task_dir.exists() else None
        else:
            path = self.output_dir
        
        if not path or not path.exists():
            return 0
        
        total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return total_size
    
    def cleanup_task(self, task_id: str) -> bool:
        """
        Delete all screenshots for a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if successful
        """
        try:
            task_dir = self.output_dir / task_id
            if task_dir.exists():
                import shutil
                shutil.rmtree(task_dir)
                logger.info(f"Cleaned up screenshots for task: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup task {task_id}: {e}")
            return False
