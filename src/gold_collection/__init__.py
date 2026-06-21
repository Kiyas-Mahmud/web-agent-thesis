"""Leakage-safe gold dataset collection utilities."""

from .gold_schema import (
    COARSE_FAILURE_LABELS,
    FORBIDDEN_TRAINING_FIELDS,
    RECOVERY_LABELS,
    GoldStep,
    GoldTrajectory,
    normalize_fine_failure,
    normalize_recovery,
    map_fine_to_coarse,
)
from .gold_collector import GoldCollector, GoldCollectionConfig
from .gold_exporter import GoldExporter, GoldExportConfig

__all__ = [
    "COARSE_FAILURE_LABELS",
    "FORBIDDEN_TRAINING_FIELDS",
    "RECOVERY_LABELS",
    "GoldStep",
    "GoldTrajectory",
    "normalize_fine_failure",
    "normalize_recovery",
    "map_fine_to_coarse",
    "GoldCollector",
    "GoldCollectionConfig",
    "GoldExporter",
    "GoldExportConfig",
]
