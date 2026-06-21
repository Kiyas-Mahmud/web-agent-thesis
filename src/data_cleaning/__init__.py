"""
Data Cleaning & Splitting Module

Provides data cleaning, validation, and splitting pipelines:
- Duplicate detection and removal
- Incomplete trajectory filtering
- Schema validation
- Anomaly detection
- Domain-aware splitting
- Stratified failure distribution
- Statistics and reporting
"""

from .cleaning_schema import (
    ValidationRule,
    SplitConfig,
    CleaningResult,
    ValidationResult,
    SplitResult,
    DatasetStatistics,
    QualityMetrics,
    DEFAULT_VALIDATION_RULES,
    DEFAULT_SPLIT_CONFIG,
)

from .data_cleaner import (
    DataCleaner,
    validate_trajectory_schema,
    check_image_files,
    detect_duplicates,
    filter_incomplete_trajectories,
)

from .dataset_splitter import (
    DatasetSplitter,
    split_by_domain,
    stratify_by_failure,
    validate_no_leakage,
)

__all__ = [
    # Schema
    "ValidationRule",
    "SplitConfig",
    "CleaningResult",
    "ValidationResult",
    "SplitResult",
    "DatasetStatistics",
    "QualityMetrics",
    "DEFAULT_VALIDATION_RULES",
    "DEFAULT_SPLIT_CONFIG",
    
    # Cleaner
    "DataCleaner",
    "validate_trajectory_schema",
    "check_image_files",
    "detect_duplicates",
    "filter_incomplete_trajectories",
    
    # Splitter
    "DatasetSplitter",
    "split_by_domain",
    "stratify_by_failure",
    "validate_no_leakage",
]
