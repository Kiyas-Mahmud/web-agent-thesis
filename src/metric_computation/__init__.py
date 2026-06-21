"""
Metric Computation Module

Computes visual difference scores, state hashes, and other quantitative metrics
for detecting state changes and failures in web interaction trajectories.
"""

from .metric_schema import (
    StepMetrics,
    TrajectoryMetrics,
    VisualMetrics,
    StateHashMetrics,
    PerformanceMetrics,
    MetricThresholds,
    ChangeLevel
)

from .visual_metrics import VisualMetricsComputer
from .state_hash import StateHashComputer
from .metric_computer import MetricComputer

__all__ = [
    'StepMetrics',
    'TrajectoryMetrics',
    'VisualMetrics',
    'StateHashMetrics',
    'PerformanceMetrics',
    'MetricThresholds',
    'ChangeLevel',
    'VisualMetricsComputer',
    'StateHashComputer',
    'MetricComputer'
]
