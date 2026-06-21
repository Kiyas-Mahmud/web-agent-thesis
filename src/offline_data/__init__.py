"""
Offline data infrastructure for failure injection approach.

This module handles loading pre-captured datasets (Multimodal Mind2Web)
and building offline augmented trajectories without live browser replay.
"""

from .offline_schema import (
    OfflineStep,
    OfflineTrajectory,
    AugmentedStep,
    AugmentedTrajectory,
)
from .mind2web_loader import MultimodalMind2WebLoader

__all__ = [
    "OfflineStep",
    "OfflineTrajectory",
    "AugmentedStep",
    "AugmentedTrajectory",
    "MultimodalMind2WebLoader",
]
