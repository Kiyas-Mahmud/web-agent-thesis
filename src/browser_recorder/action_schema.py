"""
Action Schema

Defines action types and structures for browser interactions.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import time


class ActionType(str, Enum):
    """Types of browser actions"""
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    SELECT = "SELECT"
    NAVIGATE = "NAVIGATE"
    WAIT = "WAIT"
    HOVER = "HOVER"
    PRESS_KEY = "PRESS_KEY"


class Action(BaseModel):
    """
    Represents a single browser action to be executed.
    """
    action_type: ActionType = Field(..., description="Type of action to perform")
    target: Optional[str] = Field(None, description="CSS selector or coordinates")
    value: Optional[str] = Field(None, description="Value for input (TYPE action)")
    timeout: Optional[int] = Field(30000, description="Timeout in milliseconds")
    description: Optional[str] = Field(None, description="Human-readable action description")
    
    # Optional parameters for specific actions
    coordinates: Optional[Dict[str, int]] = Field(None, description="X,Y coordinates for CLICK")
    scroll_amount: Optional[int] = Field(None, description="Pixels to scroll")
    key: Optional[str] = Field(None, description="Key to press (e.g., 'Enter')")
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary"""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Create action from dictionary"""
        return cls(**data)


class ActionResult(BaseModel):
    """
    Result of executing an action.
    """
    success: bool = Field(..., description="Whether action succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    element_found: bool = Field(True, description="Whether target element was found")
    
    # Additional context
    final_url: Optional[str] = Field(None, description="URL after action")
    page_title: Optional[str] = Field(None, description="Page title after action")
    
    # Page health status (for NAVIGATE actions)
    page_status: Optional[str] = Field(None, description="Page load status: LOADED, ERROR_PAGE, TIMEOUT, REDIRECT_LOOP")
    http_status: Optional[int] = Field(None, description="HTTP status code")
    dom_ready_state: Optional[str] = Field(None, description="DOM ready state: complete, interactive, loading")
    navigation_error: Optional[str] = Field(None, description="Navigation error message if any")
    is_error_page: Optional[bool] = Field(None, description="Whether page is an error page (chrome-error://, etc.)")
    
    class Config:
        use_enum_values = True


class Step(BaseModel):
    """
    Represents a complete interaction step (action + before/after states).
    """
    step_id: int = Field(..., description="Sequential step identifier")
    action: Action = Field(..., description="The action performed")
    result: ActionResult = Field(..., description="Result of the action")
    
    # State captures
    screenshot_before: Optional[str] = Field(None, description="Path to before screenshot")
    screenshot_after: Optional[str] = Field(None, description="Path to after screenshot")
    
    # Timing
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")
    
    # Browser state
    url_before: Optional[str] = Field(None, description="URL before action")
    url_after: Optional[str] = Field(None, description="URL after action")
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary"""
        data = self.model_dump()
        # Convert action and result to dicts
        data['action'] = self.action.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        """Create step from dictionary"""
        # Convert nested dicts back to models
        if 'action' in data and isinstance(data['action'], dict):
            data['action'] = Action.from_dict(data['action'])
        return cls(**data)


class Trajectory(BaseModel):
    """
    A complete trajectory (sequence of steps) for a task.
    """
    task_id: str = Field(..., description="Associated task ID")
    steps: List[Step] = Field(default_factory=list, description="Sequence of steps")
    
    # Metadata
    start_time: float = Field(default_factory=time.time, description="Start timestamp")
    end_time: Optional[float] = Field(None, description="End timestamp")
    success: bool = Field(False, description="Whether task completed successfully")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # URLs
    start_url: str = Field(..., description="Initial URL")
    final_url: Optional[str] = Field(None, description="Final URL")
    
    class Config:
        use_enum_values = True
    
    def add_step(self, step: Step):
        """Add a step to the trajectory"""
        self.steps.append(step)
    
    def get_step_count(self) -> int:
        """Get number of steps"""
        return len(self.steps)
    
    def get_steps(self) -> List['Step']:
        """Get all steps"""
        return self.steps
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trajectory to dictionary"""
        data = self.model_dump()
        # Convert steps to dicts
        data['steps'] = [step.to_dict() for step in self.steps]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trajectory':
        """Create trajectory from dictionary"""
        # Convert steps back to Step objects
        if 'steps' in data:
            data['steps'] = [Step.from_dict(s) if isinstance(s, dict) else s 
                           for s in data['steps']]
        return cls(**data)
    
    def get_duration(self) -> float:
        """Get total duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
