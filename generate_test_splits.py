"""
Generate augmented dataset from TEST SPLITS ONLY.

Uses IDENTICAL settings to generate_70k_safe.py to ensure consistency:
- Image size: 256px width
- Image quality: 60% JPEG
- Batch size: 5 trajectories
- Injectors: TARGET_MISSING, MISCLICK, WRONG_OPERATION, LOOP
- 3 passes with seeds 42, 100, 200
- Injection rates: 70%, 75%, 72%

Processes: test_domain, test_task, test_website
Skips: train (already have 23,325 steps from it)

Output: Appends to output/dataset_70k_safe/ (same folder as existing data)
"""

import json
import logging
import random
import time
from pathlib import Path
from collections import Counter
from PIL import Image
import gc
import sys

from src.offline_data.mind2web_loader import MultimodalMind2WebLoader
from src.failure_injection.injection_engine import InjectionPipeline, InjectionConfig
from src.failure_injection.target_missing import TargetMissingInjector
from src.failure_injection.misclick import MisclickInjector
from src.failure_injection.wrong_operation import WrongOperationInjector
from src.failure_injection.loop import LoopInjector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_generation_test_splits.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── IDENTICAL SETTINGS to generate_70k_safe.py ─────────────────────────
OUTPUT_DIR = Path("output/dataset_70k_safe")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_SIZE = 5          # Same as existing
IMAGE_WIDTH = 256       # Same as existing
IMAGE_QUALITY = 60      # Same as existing

# Same 3 passes with same seeds and injection rates
PASSES = [
    {"name": "pass1", "seed": 42, "injection_rate": 0.70},
    {"name": "pass2", "seed": 100, "injection_rate": 0.75},
    {"name": "pass3", "seed": 200, "injection_rate": 0.72},
]

# ONLY test splits — skip train (already processed)
SPLITS_TO_PROCESS = ['test_domain', 'test_task', 'test_website']


def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot with same optimization as existing dataset."""
    try:
        if image is None:
            return False
        
        # Resize to 256px width (same as existing)
        if image.width > IMAGE_WIDTH:
            ratio = IMAGE_WIDTH / image.width
            new_height = int(image.height * ratio)
            image = image.resize((IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, "JPEG", quality=IMAGE_QUALITY, optimize=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to save screenshot {path}: {e}")
        return False


def serialize_step(aug_step, task_id: str, step_idx: int, pass_name: str, split_name: str) -> dict:
    """Serialize step with IDENTICAL schema to existing dataset."""
    # Same folder naming convention
    task_folder = f"{split_name}_{pass_name}_{task_id}"
    task_dir = IMAGES_DIR / task_folder
    task_dir.mkdir(parents=True, exist_ok=True)
    
    orig_step = aug_step.original_step
    
    # Same image naming convention
    before_path = task_dir / f"step_{step_idx:04d}_before.jpg"
    after_path = task_dir / f"step_{step_idx:04d}_after.jpg"
    
    before_saved = False
    after_saved = False
    
    before_img = aug_step.state_before_modified if aug_step.state_before_modified else orig_step.state_before
    after_img = aug_step.state_after_modified if aug_step.state_after_modified else orig_step.state_after
    
    if before_img:
        before_saved = save_screenshot(before_img, before_path)
    if after_img:
        after_saved = save_screenshot(after_img, after_path)
    
    # IDENTICAL JSON schema to existing data
    return {
        'task_id': f"{split_name}_{pass_name}_{task_id}_{step_idx}",
        'original_task_id': task_id,
        'split': split_name,
        'pass': pass_name,
        'annotation_id': orig_step.annotation_id,
        'action_type': orig_step.action_type,
        'action_target': orig_step.action_target,
        'action_target_bbox': orig_step.target_bbox,
        'state_before_path': str(before_path.relative_to(OUTPUT_DIR)) if before_saved else None,
        'state_after_path': str(after_path.relative_to(OUTPUT_DIR)) if after_saved else None,
        'is_augmented': aug_step.is_augmented,
        'injection_type': aug_step.injection_type if aug_step.is_augmented else None,
        'failure_reason': aug_step.root_cause if aug_step.is_augmented else None,
        'recovery_action': aug_step.recovery_strategy if aug_step.is_augmented else None,
    }


def process_batch(batch_trajs, pipeline, pass_name: str, split_name: str, batch_idx: int, total_batches: int):
    """Process a batch of trajectories."""
    logger.info(f"    Batch {batch_idx}/{total_batches}: Processing {len(batch_trajs)} trajectories...")
    
    batch_steps = []
    clean_count = 0
    augmented_count = 0
    failure_counts = Counter()
    
    for traj in batch_trajs:
        try:
            aug_traj = pipeline.augment_trajectory(traj)
            
            for step_idx, aug_step in enumerate(aug_traj.augmented_steps):
                serialized = serialize_step(aug_step, traj.task_id, step_idx, pass_name, split_name)
                batch_steps.append(serialized)
                
                if aug_step.is_augmented:
                    augmented_count += 1
                    failure_counts[aug_step.injection_type] += 1
                else:
                    clean_count += 1
            
            del aug_traj
            
        except Exception as e:
            logger.warning(f"      Failed trajectory {traj.task_id}: {e}")
            continue
    
    gc.collect()
    
    logger.info(f"      Clean: {clean_count}, Augmented: {augmented_count}")
    return batch_steps, clean_count, augmented_count, failure_counts


def process_split(loader, split: str, pipeline, pass_name: str):
    """Process a single split in batches."""
    logger.info(f"\n  Processing {split} split...")
    
    try:
        logger.info(f"    Loading trajectory list...")
        metadata_trajs = loader.load_trajectories(split=split, limit=None, load_screenshots=False)
        logger.info(f"    Found {len(metadata_trajs)} trajectories")
        
        if len(metadata_trajs) == 0:
            logger.warning(f"    No trajectories found in {split} split!")
            return [], 0, 0, Counter()
        
        task_ids = [t.task_id for t in metadata_trajs]
        total_trajs = len(task_ids)
        
        all_steps = []
        total_clean = 0
        total_augmented = 0
        total_failures = Counter()
        
        for batch_start in range(0, total_trajs, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_trajs)
            batch_ids = task_ids[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (total_trajs + BATCH_SIZE - 1) // BATCH_SIZE
            
            try:
                batch_trajs = loader.load_trajectories(
                    split=split,
                    filter_by_ids=batch_ids,
                    load_screenshots=True
                )
                
                batch_steps, clean, aug, failures = process_batch(
                    batch_trajs, pipeline, pass_name, split, batch_num, total_batches
                )
                
                all_steps.extend(batch_steps)
                total_clean += clean
                total_augmented += aug
                total_failures.update(failures)
                
                del batch_trajs
                gc.collect()
                
            except Exception as e:
                logger.error(f"    Batch {batch_num} failed: {e}")
                continue
        
        logger.info(f"  {split} complete: {total_clean} clean, {total_augmented} augmented")
        return all_steps, total_clean, total_augmented, total_failures
        
    except Exception as e:
        logger.error(f"  Split {split} failed completely: {e}")
        return [], 0, 0, Counter()


def save_progress(split_name: str, pass_name: str, steps: list, stats: dict):
    """Save progress for a split+pass combination."""
    progress_dir = OUTPUT_DIR / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)
    
    steps_file = progress_dir / f"{split_name}_{pass_name}_steps.json"
    with open(steps_file, 'w') as f:
        json.dump(steps, f, indent=2)
    
    stats_file = progress_dir / f"{split_name}_{pass_name}_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"  Progress saved: {steps_file.name}")


def main():
    logger.info("=" * 70)
    logger.info("TEST SPLITS AUGMENTED DATASET GENERATION")
    logger.info("=" * 70)
    logger.info(f"Settings (IDENTICAL to existing train data):")
    logger.info(f"  - Image size: {IMAGE_WIDTH}px")
    logger.info(f"  - Image quality: {IMAGE_QUALITY}%")
    logger.info(f"  - Batch size: {BATCH_SIZE} trajectories")
    logger.info(f"  - Injectors: TARGET_MISSING, MISCLICK, WRONG_OPERATION, LOOP")
    logger.info(f"  - Passes: {len(PASSES)}")
    logger.info(f"  - Splits: {SPLITS_TO_PROCESS}")
    logger.info(f"  - Train: SKIPPED (already have 23,325 steps)")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load dataset from cache (ONLY test splits to save memory)
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
    logger.info("Loading test splits from HuggingFace cache...")
    success = loader.load_from_cache(splits_to_load=SPLITS_TO_PROCESS)
    if not success:
        logger.error("Failed to load dataset from cache!")
        sys.exit(1)
    
    # Load existing data to merge later
    existing_file = OUTPUT_DIR / "augmented_trajectories.json"
    existing_steps = []
    if existing_file.exists():
        logger.info(f"\nLoading existing data from {existing_file}...")
        with open(existing_file, 'r') as f:
            existing_steps = json.load(f)
        logger.info(f"Existing steps: {len(existing_steps):,}")
    
    # Track new data
    new_steps = []
    grand_total_clean = 0
    grand_total_augmented = 0
    grand_total_failures = Counter()
    
    # Process each pass
    for pass_idx, pass_config in enumerate(PASSES, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"PASS {pass_idx}/{len(PASSES)}: {pass_config['name']}")
        logger.info(f"Seed: {pass_config['seed']}, Injection Rate: {pass_config['injection_rate']*100:.0f}%")
        logger.info(f"{'='*70}")
        
        random.seed(pass_config['seed'])
        
        # Same injection pipeline as existing
        config = InjectionConfig(
            injection_rate=pass_config['injection_rate'],
            random_seed=pass_config['seed']
        )
        pipeline = InjectionPipeline(config)
        pipeline.register_injector(TargetMissingInjector(config))
        pipeline.register_injector(MisclickInjector(config))
        pipeline.register_injector(WrongOperationInjector(config))
        pipeline.register_injector(LoopInjector(config))
        
        # Process ONLY test splits
        for split_idx, split in enumerate(SPLITS_TO_PROCESS, 1):
            logger.info(f"\n--- Split {split_idx}/{len(SPLITS_TO_PROCESS)}: {split} ---")
            
            steps, clean, aug, failures = process_split(
                loader, split, pipeline, pass_config['name']
            )
            
            if len(steps) > 0:
                save_progress(split, pass_config['name'], steps, {
                    'clean': clean,
                    'augmented': aug,
                    'failures': dict(failures)
                })
                
                new_steps.extend(steps)
                grand_total_clean += clean
                grand_total_augmented += aug
                grand_total_failures.update(failures)
            
            gc.collect()
        
        logger.info(f"\nPass {pass_idx} complete! New steps so far: {len(new_steps):,}")
        gc.collect()
    
    # ── Merge with existing data ────────────────────────────────────────
    logger.info(f"\n{'='*70}")
    logger.info("MERGING WITH EXISTING DATASET")
    logger.info(f"{'='*70}")
    
    all_steps = existing_steps + new_steps
    logger.info(f"Existing (train): {len(existing_steps):,} steps")
    logger.info(f"New (test splits): {len(new_steps):,} steps")
    logger.info(f"TOTAL MERGED: {len(all_steps):,} steps")
    
    # Save merged dataset
    logger.info(f"\nWriting merged dataset to {existing_file}...")
    with open(existing_file, 'w') as f:
        json.dump(all_steps, f, indent=2)
    
    # Also save test-splits-only file for reference
    test_only_file = OUTPUT_DIR / "augmented_trajectories_test_splits.json"
    with open(test_only_file, 'w') as f:
        json.dump(new_steps, f, indent=2)
    logger.info(f"Test-only data saved to: {test_only_file}")
    
    # Update summary
    # Count existing train stats
    existing_clean = sum(1 for s in existing_steps if not s.get('is_augmented', False))
    existing_aug = sum(1 for s in existing_steps if s.get('is_augmented', False))
    
    summary = {
        'total_steps': len(all_steps),
        'clean_steps': existing_clean + grand_total_clean,
        'augmented_steps': existing_aug + grand_total_augmented,
        'failure_distribution': {},
        'passes': len(PASSES),
        'splits': ['train'] + SPLITS_TO_PROCESS,
        'breakdown': {
            'train': len(existing_steps),
            'test_domain': sum(1 for s in new_steps if s['split'] == 'test_domain'),
            'test_task': sum(1 for s in new_steps if s['split'] == 'test_task'),
            'test_website': sum(1 for s in new_steps if s['split'] == 'test_website'),
        },
        'configuration': {
            'image_width': IMAGE_WIDTH,
            'image_quality': IMAGE_QUALITY,
            'batch_size': BATCH_SIZE,
            'injectors': ['TARGET_MISSING', 'MISCLICK', 'WRONG_OPERATION', 'LOOP'],
            'injectors_skipped': ['NO_STATE_CHANGE'],
        },
        'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Count failure distribution across ALL data
    all_failures = Counter()
    for s in all_steps:
        if s.get('is_augmented') and s.get('injection_type'):
            all_failures[s['injection_type']] += 1
    summary['failure_distribution'] = dict(all_failures)
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final summary
    logger.info(f"\n{'='*70}")
    logger.info("GENERATION COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Total Steps: {len(all_steps):,}")
    logger.info(f"  From train: {len(existing_steps):,}")
    logger.info(f"  From test splits: {len(new_steps):,}")
    logger.info(f"    Clean: {grand_total_clean:,}")
    logger.info(f"    Augmented: {grand_total_augmented:,}")
    logger.info(f"\nFailure Distribution (new test data):")
    for ftype, count in grand_total_failures.most_common():
        pct = count / grand_total_augmented * 100 if grand_total_augmented > 0 else 0
        logger.info(f"  {ftype}: {count:,} ({pct:.1f}%)")
    logger.info(f"\nOutput:")
    logger.info(f"  Merged: {existing_file}")
    logger.info(f"  Test-only: {test_only_file}")
    logger.info(f"  Summary: {summary_file}")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)
