"""
Session Manager

Handles browser session lifecycle, context management, and crash recovery.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import logging
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages browser sessions with Playwright.
    Handles initialization, cleanup, and crash recovery.
    """
    
    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: int = 30000,
        user_agent: Optional[str] = None
    ):
        """
        Initialize SessionManager.
        
        Args:
            headless: Run browser in headless mode
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            timeout: Default timeout in milliseconds
            user_agent: Custom user agent string
        """
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # Session state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        self._is_initialized = False
        
        logger.info("SessionManager initialized")
    
    async def initialize(self):
        """Initialize Playwright and browser"""
        if self._is_initialized:
            logger.warning("Session already initialized")
            return
        
        try:
            logger.info("Starting Playwright...")
            self._playwright = await async_playwright().start()
            
            logger.info("Launching browser...")
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-http2',
                ]
            )
            
            self._is_initialized = True
            logger.info("Browser launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def create_context(self) -> BrowserContext:
        """
        Create a new browser context (isolated session).
        
        Returns:
            BrowserContext object
        """
        if not self._is_initialized or not self._browser:
            await self.initialize()
        
        try:
            self._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent=self.user_agent,
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Set default timeout
            self._context.set_default_timeout(self.timeout)
            
            logger.info("Browser context created")
            return self._context
            
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            raise
    
    async def create_page(self, url: Optional[str] = None) -> Page:
        """
        Create a new page in the current context.
        
        Args:
            url: Optional URL to navigate to
        
        Returns:
            Page object
        """
        if not self._context:
            await self.create_context()
        
        try:
            self._page = await self._context.new_page()
            
            logger.info("New page created")
            
            if url:
                await self.navigate_to(url)
            
            return self._page
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            raise
    
    async def navigate_to(self, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        """
        Navigate to a URL with full page status detection.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
        
        Returns:
            Dict with navigation result and page health status
        """
        if not self._page:
            raise RuntimeError("No page available. Call create_page() first.")
        
        navigation_error = None
        http_status = None
        
        try:
            logger.info(f"Navigating to: {url}")
            response = await self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
            
            # Get HTTP status if response available
            if response:
                http_status = response.status
            
            logger.info(f"Navigation successful: {url}")
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            navigation_error = str(e)
        
        # Get page health status after navigation
        page_health = await self._get_page_health_status(navigation_error, http_status)
        
        return {
            "success": page_health["page_status"] == "LOADED",
            "page_status": page_health["page_status"],
            "http_status": page_health["http_status"],
            "dom_ready_state": page_health["dom_ready_state"],
            "navigation_error": page_health["navigation_error"],
            "is_error_page": page_health["is_error_page"],
            "final_url": page_health["final_url"]
        }
    
    async def _get_page_health_status(self, navigation_error: Optional[str], http_status: Optional[int]) -> Dict[str, Any]:
        """
        Detect page health status after navigation.
        
        Returns:
            Dict with page health indicators
        """
        if not self._page:
            return {
                "page_status": "ERROR_PAGE",
                "http_status": None,
                "dom_ready_state": "loading",
                "navigation_error": "No page available",
                "is_error_page": True,
                "final_url": ""
            }
        
        try:
            final_url = self._page.url
            
            # Check for error page schemes
            is_error_page = any(scheme in final_url for scheme in [
                "chrome-error://",
                "about:blank",
                "about:srcdoc",
                "data:text/html"
            ])
            
            # Get DOM ready state
            try:
                dom_ready_state = await self._page.evaluate("document.readyState")
            except:
                dom_ready_state = "loading"
            
            # Determine page status
            if is_error_page:
                page_status = "ERROR_PAGE"
            elif navigation_error:
                if "timeout" in navigation_error.lower():
                    page_status = "TIMEOUT"
                elif "redirect" in navigation_error.lower() or "too many redirects" in navigation_error.lower():
                    page_status = "REDIRECT_LOOP"
                else:
                    page_status = "ERROR_PAGE"
            elif http_status and http_status >= 400:
                page_status = "ERROR_PAGE"
            elif dom_ready_state == "complete" and not is_error_page:
                page_status = "LOADED"
            else:
                page_status = "TIMEOUT"
            
            return {
                "page_status": page_status,
                "http_status": http_status,
                "dom_ready_state": dom_ready_state,
                "navigation_error": navigation_error,
                "is_error_page": is_error_page,
                "final_url": final_url
            }
            
        except Exception as e:
            logger.error(f"Error detecting page health: {e}")
            return {
                "page_status": "ERROR_PAGE",
                "http_status": http_status,
                "dom_ready_state": "loading",
                "navigation_error": str(e),
                "is_error_page": True,
                "final_url": ""
            }
    
    async def wait_for_stability(self, timeout: int = 5000) -> bool:
        """
        Wait for page to stabilize (no network activity).
        
        Args:
            timeout: Maximum wait time in milliseconds
        
        Returns:
            True if page stabilized
        """
        if not self._page:
            return False
        
        try:
            await self._page.wait_for_load_state("networkidle", timeout=timeout)
            await asyncio.sleep(0.5)  # Additional small delay
            logger.debug("Page stabilized")
            return True
            
        except Exception as e:
            logger.warning(f"Stability wait timeout: {e}")
            return False
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get current page information.
        
        Returns:
            Dictionary with URL, title, etc.
        """
        if not self._page:
            return {}
        
        try:
            return {
                "url": self._page.url,
                "title": await self._page.title(),
                "viewport": self.viewport
            }
        except Exception as e:
            logger.error(f"Failed to get page info: {e}")
            return {}
    
    async def close_page(self):
        """Close the current page"""
        if self._page:
            try:
                await self._page.close()
                self._page = None
                logger.info("Page closed")
            except Exception as e:
                logger.error(f"Error closing page: {e}")
    
    async def close_context(self):
        """Close the browser context"""
        if self._context:
            try:
                await self._context.close()
                self._context = None
                logger.info("Context closed")
            except Exception as e:
                logger.error(f"Error closing context: {e}")
    
    async def close_browser(self):
        """Close the browser"""
        if self._browser:
            try:
                await self._browser.close()
                self._browser = None
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get information about the current page.
        
        Returns:
            Dictionary with page info (url, title, viewport)
        """
        if not self._page:
            return {}
        
        try:
            url = self._page.url
            title = await self._page.title()
            viewport = self._page.viewport_size
            
            return {
                'url': url,
                'title': title,
                'viewport': viewport
            }
        except Exception as e:
            logger.error(f"Error getting page info: {e}")
            return {}
    
    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up session...")
        
        await self.close_page()
        await self.close_context()
        await self.close_browser()
        
        if self._playwright:
            try:
                await self._playwright.stop()
                self._playwright = None
                logger.info("Playwright stopped")
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")
        
        self._is_initialized = False
        logger.info("Session cleanup complete")
    
    @property
    def page(self) -> Optional[Page]:
        """Get current page"""
        return self._page
    
    @property
    def context(self) -> Optional[BrowserContext]:
        """Get current context"""
        return self._context
    
    @property
    def browser(self) -> Optional[Browser]:
        """Get browser instance"""
        return self._browser
    
    @property
    def is_initialized(self) -> bool:
        """Check if session is initialized"""
        return self._is_initialized and self._browser is not None
