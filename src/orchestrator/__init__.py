"""
Collection Orchestrator Module

Provides the main pipeline orchestrator that ties together all components:
- Task loading (Task-01)
- Browser recording (Task-02)
- Metric computation (Task-03)
- Failure labeling (Task-04)
- Recovery generation (Task-05)
- Reflection annotation (Task-06)

The orchestrator manages end-to-end data collection with error handling,
progress tracking, and output management.
"""

from .orchestrator_schema import (
    CollectionConfig,
    OrchestrationResult,
    TaskResult,
    PipelineStatistics,
    DEFAULT_COLLECTION_CONFIG,
)

from .collection_orchestrator import (
    CollectionOrchestrator,
    run_collection_pipeline,
)

__all__ = [
    # Schema
    "CollectionConfig",
    "OrchestrationResult",
    "TaskResult",
    "PipelineStatistics",
    "DEFAULT_COLLECTION_CONFIG",
    
    # Orchestrator
    "CollectionOrchestrator",
    "run_collection_pipeline",
]
