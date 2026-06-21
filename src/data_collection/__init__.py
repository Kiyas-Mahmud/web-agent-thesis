"""
Data Collection Module

Streams task metadata from HuggingFace datasets and converts them
to ActionLog format for BrowserReplay.
"""

from .hf_collector import HFCollector, CollectionConfig

__all__ = ["HFCollector", "CollectionConfig"]
