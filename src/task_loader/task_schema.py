"""
Task Schema Definition

Defines the unified task schema that all sources are normalized to.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaskDifficulty(str, Enum):
    """Task difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TaskCategory(str, Enum):
    """Task categories"""
    SEARCH = "search"
    FORM_FILLING = "form_filling"
    NAVIGATION = "navigation"
    SHOPPING = "shopping"
    INFORMATION_RETRIEVAL = "information_retrieval"
    INTERACTION = "interaction"
    OTHER = "other"


class TaskSource(str, Enum):
    """Dataset sources"""
    MIND2WEB = "mind2web"       # Mind2Web (HuggingFace stream) — main backbone
    MINIWOB  = "miniwob"        # MiniWoB++ (local env)  — controlled failure lab
    WEBARENA = "webarena"       # WebArena task configs   — long-horizon evaluation
    CUSTOM   = "custom"         # manually defined tasks
    # legacy aliases kept so existing JSONL files stay valid
    WAVE_UI          = "wave-ui"
    MIND2WEB_TEST    = "mind2web-test"
    WEBLINX          = "weblinx"
    VISUAL_WEBARENA  = "visual-webarena"


class TaskMetadata(BaseModel):
    """Task metadata"""
    source: TaskSource
    difficulty: Optional[TaskDifficulty] = TaskDifficulty.MEDIUM
    expected_steps: Optional[int] = None
    category: Optional[TaskCategory] = TaskCategory.OTHER
    domain_category: Optional[str] = None
    original_id: Optional[str] = None
    additional_info: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """
    Unified task schema for all data sources.
    
    This schema normalizes tasks from different sources into a consistent format.
    """
    task_id: str = Field(..., description="Unique identifier for the task")
    task_description: str = Field(..., description="Natural language description of the goal")
    website_domain: str = Field(..., description="Domain name (e.g., 'amazon.com')")
    start_url: str = Field(..., description="Initial page URL to start the task")
    metadata: TaskMetadata = Field(..., description="Additional task metadata")
    
    # Optional fields for enhanced tasks
    target_elements: Optional[List[str]] = Field(
        default=None,
        description="List of target elements/selectors if known"
    )
    expected_actions: Optional[List[str]] = Field(
        default=None,
        description="Expected sequence of actions if available"
    )
    success_criteria: Optional[str] = Field(
        default=None,
        description="How to verify task completion"
    )
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        return cls(**data)
    
    def __str__(self) -> str:
        return f"Task({self.task_id}, {self.website_domain}, {self.task_description[:50]}...)"
    
    def __repr__(self) -> str:
        return self.__str__()
