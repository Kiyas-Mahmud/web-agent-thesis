"""
Failure Labeling Module

This module provides automated failure detection, diagnosis, and categorization for
web interaction trajectories. It analyzes recorded actions, browser states, and
computed metrics to identify and classify failures into 9 distinct categories.

Key Components:
- FailureType: Enum of 9 failure categories
- ExecutionOutcome: SUCCESS, FAILURE, PARTIAL_SUCCESS
- FailureLabel: Complete failure diagnosis with confidence and evidence
- FailureDetector: Detection engine for identifying failure signals
- FailureClassifier: Rule-based categorization of failures
- DiagnosticsEngine: Evidence aggregation and confidence scoring
- FailureLabeler: Main orchestration class

Usage:
    from failure_labeling import FailureLabeler, FailureType
    
    labeler = FailureLabeler()
    labeled_trajectory = labeler.process_trajectory_file("trajectory.jsonl")
"""

from .failure_schema import (
    FailureType,
    ExecutionOutcome,
    FailureEvidence,
    FailureLabel,
    LabeledStep,
    LabeledTrajectory,
    DiagnosticConfig,
)

from .failure_detector import (
    FailureDetector,
    FailureSignal,
    SignalType,
)

from .failure_classifier import (
    FailureClassifier,
    ClassificationRule,
)

from .diagnostics_engine import (
    DiagnosticsEngine,
    EvidenceAggregator,
)

from .failure_labeler import (
    FailureLabeler,
)

from .decision_tree import (
    classify_step,
    FailureClassification,
    RECOVERY_STRATEGY,
    SEVERITY,
)

__all__ = [
    # Enums and schemas
    "FailureType",
    "ExecutionOutcome",
    "FailureEvidence",
    "FailureLabel",
    "LabeledStep",
    "LabeledTrajectory",
    "DiagnosticConfig",
    
    # Detection
    "FailureDetector",
    "FailureSignal",
    "SignalType",
    
    # Classification
    "FailureClassifier",
    "ClassificationRule",
    
    # Diagnostics
    "DiagnosticsEngine",
    "EvidenceAggregator",
    
    # Main interface
    "FailureLabeler",
]
