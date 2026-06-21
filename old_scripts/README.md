# Archived Scripts

These scripts were archived on 2026-02-22 due to critical bugs.

## Files

### generate_dataset_batch.py (BUGGY - DO NOT USE)

**Problem:** Duplicate data bug - loaded same 50 trajectories repeatedly

- Result: 957 trajectories generated but only 50 unique (95% duplicates)
- Root cause: `load_trajectories(limit=50)` always returned first 50, not next 50
- Status: REPLACED by `generate_10k_dataset.py`

### RUN_DATASET_GENERATION.bat

**Problem:** Launches buggy generate_dataset_batch.py

- Status: REPLACED by `RUN_10K_GENERATION.bat`

### run_step5_generate_1000_tasks.bat

**Problem:** Part of old pipeline with duplicate bug

- Status: REPLACED by new 10K generation pipeline

## Replacement

Use these new scripts instead:

- **generate_10k_dataset.py** - Fixed version, no duplicates
- **RUN_10K_GENERATION.bat** - Launcher for fixed version
- **validate_10k_dataset.py** - Quality validation with duplicate detection

## What Was Fixed

1. Load ALL trajectories ONCE (not repeatedly)
2. Shuffle for randomness
3. Process until target steps reached
4. Filter null/invalid data
5. Built-in duplicate detection
6. Proper batch processing for memory safety
