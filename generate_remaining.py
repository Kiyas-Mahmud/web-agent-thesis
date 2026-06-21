"""
Generate REMAINING augmented data to reach 70k target.

Current: 42,579 steps (passes 1-3 on train + test splits)
Target:  70,000+ steps
Plan:    Passes 4 & 5 on ALL splits = ~28,386 more steps
Expected total: ~70,965 steps

Uses IDENTICAL settings to existing data.
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
        logging.FileHandler('dataset_generation_remaining.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── IDENTICAL SETTINGS ──────────────────────────────────────────────────
OUTPUT_DIR = Path("output/dataset_70k_safe")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_SIZE = 5
IMAGE_WIDTH = 256
IMAGE_QUALITY = 60

# NEW passes with NEW seeds (4 and 5)
PASSES = [
    {"name": "pass4", "seed": 300, "injection_rate": 0.70},
    {"name": "pass5", "seed": 400, "injection_rate": 0.73},
]

# ALL splits this time
SPLITS_TO_PROCESS = ['train', 'test_domain', 'test_task', 'test_website']


def save_screenshot(image, path):
    try:
        if image is None:
            return False
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


def serialize_step(aug_step, task_id, step_idx, pass_name, split_name):
    task_folder = f"{split_name}_{pass_name}_{task_id}"
    task_dir = IMAGES_DIR / task_folder
    task_dir.mkdir(parents=True, exist_ok=True)

    orig_step = aug_step.original_step

    before_path = task_dir / f"step_{step_idx:04d}_before.jpg"
    after_path = task_dir / f"step_{step_idx:04d}_after.jpg"

    before_img = aug_step.state_before_modified if aug_step.state_before_modified else orig_step.state_before
    after_img = aug_step.state_after_modified if aug_step.state_after_modified else orig_step.state_after

    before_saved = save_screenshot(before_img, before_path) if before_img else False
    after_saved = save_screenshot(after_img, after_path) if after_img else False

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


def process_batch(batch_trajs, pipeline, pass_name, split_name, batch_idx, total_batches):
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
            logger.warning(f"Failed trajectory {traj.task_id}: {e}")
            continue

    gc.collect()
    if batch_idx % 10 == 0:
        logger.info(f"    Batch {batch_idx}/{total_batches}: {clean_count} clean, {augmented_count} augmented")
    return batch_steps, clean_count, augmented_count, failure_counts


def process_split(loader, split, pipeline, pass_name):
    logger.info(f"\n  Processing {split} split...")
    try:
        metadata_trajs = loader.load_trajectories(split=split, limit=None, load_screenshots=False)
        logger.info(f"    Found {len(metadata_trajs)} trajectories")

        if len(metadata_trajs) == 0:
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

        logger.info(f"  {split} complete: {total_clean} clean, {total_augmented} augmented, total {len(all_steps)} steps")
        return all_steps, total_clean, total_augmented, total_failures

    except Exception as e:
        logger.error(f"  Split {split} failed: {e}")
        return [], 0, 0, Counter()


def main():
    logger.info("=" * 70)
    logger.info("REMAINING PASSES TO REACH 70K TARGET")
    logger.info("=" * 70)
    logger.info(f"Passes: {[p['name'] for p in PASSES]}")
    logger.info(f"Splits: {SPLITS_TO_PROCESS}")
    logger.info(f"Image: {IMAGE_WIDTH}px, {IMAGE_QUALITY}% JPEG")
    logger.info("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing data
    existing_file = OUTPUT_DIR / "augmented_trajectories.json"
    existing_steps = []
    if existing_file.exists():
        with open(existing_file, 'r') as f:
            existing_steps = json.load(f)
        logger.info(f"Existing steps: {len(existing_steps):,}")

    new_steps = []
    grand_total_clean = 0
    grand_total_augmented = 0
    grand_total_failures = Counter()

    for pass_idx, pass_config in enumerate(PASSES, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"PASS {pass_config['name']} (seed={pass_config['seed']}, rate={pass_config['injection_rate']*100:.0f}%)")
        logger.info(f"{'='*70}")

        random.seed(pass_config['seed'])

        config = InjectionConfig(
            injection_rate=pass_config['injection_rate'],
            random_seed=pass_config['seed']
        )
        pipeline = InjectionPipeline(config)
        pipeline.register_injector(TargetMissingInjector(config))
        pipeline.register_injector(MisclickInjector(config))
        pipeline.register_injector(WrongOperationInjector(config))
        pipeline.register_injector(LoopInjector(config))

        for split in SPLITS_TO_PROCESS:
            # Load only the split we need right now (memory safe)
            loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
            success = loader.load_from_cache(splits_to_load=[split])
            if not success:
                logger.error(f"Failed to load {split}!")
                continue

            steps, clean, aug, failures = process_split(
                loader, split, pipeline, pass_config['name']
            )

            if len(steps) > 0:
                # Save progress file
                progress_dir = OUTPUT_DIR / "progress"
                progress_dir.mkdir(parents=True, exist_ok=True)
                progress_file = progress_dir / f"{split}_{pass_config['name']}_steps.json"
                with open(progress_file, 'w') as f:
                    json.dump(steps, f)
                logger.info(f"  Progress saved: {progress_file.name}")

                new_steps.extend(steps)
                grand_total_clean += clean
                grand_total_augmented += aug
                grand_total_failures.update(failures)

            # Free the loader memory before loading next split
            del loader
            gc.collect()

        logger.info(f"\n{pass_config['name']} complete! New steps so far: {len(new_steps):,}")
        gc.collect()

    # ── Merge ───────────────────────────────────────────────────────────
    logger.info(f"\n{'='*70}")
    logger.info("MERGING WITH EXISTING DATASET")
    logger.info(f"{'='*70}")

    all_steps = existing_steps + new_steps
    logger.info(f"Existing: {len(existing_steps):,}")
    logger.info(f"New:      {len(new_steps):,}")
    logger.info(f"TOTAL:    {len(all_steps):,}")

    with open(existing_file, 'w') as f:
        json.dump(all_steps, f, indent=2)
    logger.info(f"Saved merged dataset: {existing_file}")

    # Update summary
    all_failures = Counter()
    for s in all_steps:
        if s.get('is_augmented') and s.get('injection_type'):
            all_failures[s['injection_type']] += 1

    summary = {
        'total_steps': len(all_steps),
        'splits': SPLITS_TO_PROCESS,
        'total_passes': 5,
        'breakdown': {
            split: sum(1 for s in all_steps if s['split'] == split)
            for split in ['train', 'test_domain', 'test_task', 'test_website']
        },
        'failure_distribution': dict(all_failures),
        'configuration': {
            'image_width': IMAGE_WIDTH,
            'image_quality': IMAGE_QUALITY,
            'injectors': ['TARGET_MISSING', 'MISCLICK', 'WRONG_OPERATION', 'LOOP'],
        },
        'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    with open(OUTPUT_DIR / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n{'='*70}")
    logger.info("GENERATION COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"TOTAL DATASET: {len(all_steps):,} steps")
    logger.info(f"  Existing: {len(existing_steps):,}")
    logger.info(f"  New:      {len(new_steps):,}")
    logger.info(f"\nFailure Distribution (all data):")
    for ftype, count in all_failures.most_common():
        logger.info(f"  {ftype}: {count:,}")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)
