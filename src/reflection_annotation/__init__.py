"""
Reflection Annotation Module

Adds introspective annotation layers to capture:
- Agent confidence scores (before/after actions)
- Natural language reflection texts
- Memory update signals for learning systems
- Confidence calibration metrics

Integrates with:
- Task-04 (Failure Labeling): Uses failure diagnostics
- Task-05 (Recovery Generation): Uses recovery information
"""

from .reflection_schema import (
    MemoryType,
    ReasoningType,
    UncertaintySource,
    IntrospectionMetadata,
    ReflectionAnnotation,
    ConfidenceCalibration,
    ReflectionConfig,
    DEFAULT_REFLECTION_CONFIG,
)

from .confidence_estimator import (
    ConfidenceEstimator,
    ConfidenceFactors,
)

from .reflection_generator import (
    ReflectionGenerator,
    ReflectionTemplate,
)

from .memory_signals import (
    MemorySignalDetector,
    analyze_memory_patterns,
)

from .reflection_annotator import (
    ReflectionAnnotator,
    batch_annotate_trajectories,
)

__all__ = [
    # Schema
    "MemoryType",
    "ReasoningType",
    "UncertaintySource",
    "IntrospectionMetadata",
    "ReflectionAnnotation",
    "ConfidenceCalibration",
    "ReflectionConfig",
    "DEFAULT_REFLECTION_CONFIG",
    
    # Confidence
    "ConfidenceEstimator",
    "ConfidenceFactors",
    
    # Reflection
    "ReflectionGenerator",
    "ReflectionTemplate",
    
    # Memory
    "MemorySignalDetector",
    "analyze_memory_patterns",
    
    # Main
    "ReflectionAnnotator",
    "batch_annotate_trajectories",
]
