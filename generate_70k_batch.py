"""
Generate 70K+ dataset using batch processing to avoid memory issues.

Strategy:
- Load each split in batches of 30 trajectories
- 5 passes with different seeds for variation
- Memory-efficient processing
"""

import json
import logging
import random
import time
from pathlib import Path
from collections import Counter
from PIL import Image
import gc

from src.offline_data.mind2web_loader import MultimodalMind2WebLoader
from src.failure_injection.injection_engine import InjectionPipeline, InjectionConfig
from src.failure_injection.target_missing import TargetMissingInjector
from src.failure_injection.misclick import MisclickInjector
from src.failure_injection.wrong_operation import WrongOperationInjector
from src.failure_injection.no_state_change import NoStateChangeInjector
from src.failure_injection.loop import LoopInjector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_generation_70k_batch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = Path("output/dataset_70k_final")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_SIZE = 10  # Process 10 trajectories at a time (reduced for memory safety)
IMAGE_WIDTH = 512
IMAGE_QUALITY = 70

# Multi-pass configuration
PASSES = [
    {"name": "pass1_clean+aug", "seed": 42, "injection_rate": 0.6},
    {"name": "pass2_extra_failures", "seed": 100, "injection_rate": 0.7},
    {"name": "pass3_balanced", "seed": 200, "injection_rate": 0.65},
    {"name": "pass4_diverse", "seed": 300, "injection_rate": 0.68},
    {"name": "pass5_final", "seed": 400, "injection_rate": 0.62},
]

SPLITS = ['train', 'test_domain', 'test_task', 'test_website']


def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot with optimization."""
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


def serialize_step(aug_step, task_id: str, step_idx: int, pass_name: str) -> dict:
    """Serialize an augmented step to JSON-compatible dict with image saving."""
    # Create unique task folder for this pass
    task_folder = f"{pass_name}_{task_id}"
    task_dir = IMAGES_DIR / task_folder
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the original step
    orig_step = aug_step.original_step
    
    # Save screenshots
    before_path = task_dir / f"step_{step_idx:04d}_before.jpg"
    after_path = task_dir / f"step_{step_idx:04d}_after.jpg"
    
    before_saved = False
    after_saved = False
    
    # Use modified screenshots if available, otherwise original
    before_img = aug_step.state_before_modified if aug_step.state_before_modified else orig_step.state_before
    after_img = aug_step.state_after_modified if aug_step.state_after_modified else orig_step.state_after
    
    if before_img:
        before_saved = save_screenshot(before_img, before_path)
    if after_img:
        after_saved = save_screenshot(after_img, after_path)
    
    return {
        'task_id': f"{pass_name}_{task_id}_{step_idx}",  # Unique ID per pass
        'original_task_id': task_id,
        'annotation_id': orig_step.annotation_id,
        'pass_name': pass_name,
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


def process_batch(batch_trajs, pipeline, pass_name: str, batch_idx: int, total_batches: int):
    """Process a batch of trajectories."""
    logger.info(f"  Batch {batch_idx}/{total_batches}: Processing {len(batch_trajs)} trajectories...")
    
    batch_steps = []
    clean_count = 0
    augmented_count = 0
    failure_counts = Counter()
    
    for traj_idx, traj in enumerate(batch_trajs):
        # Apply injection
        aug_traj = pipeline.augment_trajectory(traj)
        
        # Serialize steps
        for step_idx, aug_step in enumerate(aug_traj.augmented_steps):
            serialized = serialize_step(aug_step, traj.task_id, step_idx, pass_name)
            batch_steps.append(serialized)
            
            if aug_step.is_augmented:
                augmented_count += 1
                failure_counts[aug_step.injection_type] += 1
            else:
                clean_count += 1
        
        # Aggressive cleanup per trajectory
        if (traj_idx + 1) % 5 == 0:
            gc.collect()
    
    logger.info(f"    Clean: {clean_count}, Augmented: {augmented_count}")
    return batch_steps, clean_count, augmented_count, failure_counts


def process_split_batched(loader, split: str, pipeline, pass_name: str):
    """Process a split in batches."""
    logger.info(f"\n  Processing {split} split...")
    
    # Load metadata only (no screenshots yet)
    logger.info(f"    Loading trajectory list...")
    metadata_trajs = loader.load_trajectories(split=split, limit=None, load_screenshots=False)
    logger.info(f"    Found {len(metadata_trajs)} trajectories")
    
    # Get task IDs (which are annotation IDs)
    task_ids = [t.task_id for t in metadata_trajs]
    total_trajs = len(task_ids)
    
    # Process in batches
    all_steps = []
    total_clean = 0
    total_augmented = 0
    total_failures = Counter()
    
    for batch_start in range(0, total_trajs, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_trajs)
        batch_ids = task_ids[batch_start:batch_end]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (total_trajs + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Load this batch WITH screenshots
        batch_trajs = loader.load_trajectories(
            split=split,
            filter_by_ids=batch_ids,
            load_screenshots=True
        )
        
        # Process batch
        batch_steps, clean, aug, failures = process_batch(
            batch_trajs, pipeline, pass_name, batch_num, total_batches
        )
        
        all_steps.extend(batch_steps)
        total_clean += clean
        total_augmented += aug
        total_failures.update(failures)
        
        # Cleanup
        del batch_trajs
        gc.collect()
    
    logger.info(f"  {split} complete: {total_clean} clean, {total_augmented} augmented")
    return all_steps, total_clean, total_augmented, total_failures


def main():
    logger.info("="*70)
    logger.info("GENERATING 70K+ DATASET - BATCH PROCESSING")
    logger.info("="*70)
    logger.info(f"Strategy: {len(PASSES)} passes over {len(SPLITS)} splits")
    logger.info(f"Batch size: {BATCH_SIZE} trajectories")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("="*70)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize loader
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
    loader.load_from_cache()
    
    # Process all passes
    all_steps = []
    grand_total_clean = 0
    grand_total_augmented = 0
    grand_total_failures = Counter()
    
    for pass_idx, pass_config in enumerate(PASSES, 1):
        logger.info(f"\n{'='*70}")
        logger.info(f"PASS {pass_idx}/{len(PASSES)}: {pass_config['name']}")
        logger.info(f"Seed: {pass_config['seed']}, Injection Rate: {pass_config['injection_rate']*100:.0f}%")
        logger.info(f"{'='*70}")
        
        # Set random seed
        random.seed(pass_config['seed'])
        
        # Initialize injection pipeline
        config = InjectionConfig(
            injection_rate=pass_config['injection_rate'],
            random_seed=pass_config['seed']
        )
        pipeline = InjectionPipeline(config)
        pipeline.register_injector(TargetMissingInjector(config))
        pipeline.register_injector(MisclickInjector(config))
        pipeline.register_injector(WrongOperationInjector(config))
        pipeline.register_injector(NoStateChangeInjector(config))
        pipeline.register_injector(LoopInjector(config))
        
        # Process each split
        for split in SPLITS:
            steps, clean, aug, failures = process_split_batched(
                loader, split, pipeline, pass_config['name']
            )
            all_steps.extend(steps)
            grand_total_clean += clean
            grand_total_augmented += aug
            grand_total_failures.update(failures)
        
        logger.info(f"\nPass {pass_idx} complete!")
        gc.collect()
    
    # Save final dataset
    logger.info(f"\n{'='*70}")
    logger.info("SAVING FINAL DATASET")
    logger.info(f"{'='*70}")
    
    output_file = OUTPUT_DIR / "augmented_trajectories.json"
    with open(output_file, 'w') as f:
        json.dump(all_steps, f, indent=2)
    
    # Generate summary
    summary = {
        'total_steps': len(all_steps),
        'clean_steps': grand_total_clean,
        'augmented_steps': grand_total_augmented,
        'failure_distribution': dict(grand_total_failures),
        'passes': len(PASSES),
        'splits': SPLITS,
        'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final summary
    logger.info(f"\n{'='*70}")
    logger.info("GENERATION COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Total Steps: {len(all_steps):,}")
    logger.info(f"  Clean: {grand_total_clean:,} ({grand_total_clean/len(all_steps)*100:.1f}%)")
    logger.info(f"  Augmented: {grand_total_augmented:,} ({grand_total_augmented/len(all_steps)*100:.1f}%)")
    logger.info(f"\nFailure Distribution:")
    for ftype, count in grand_total_failures.most_common():
        pct = count / grand_total_augmented * 100 if grand_total_augmented > 0 else 0
        logger.info(f"  {ftype}: {count:,} ({pct:.1f}%)")
    logger.info(f"\nOutput Directory: {OUTPUT_DIR}")
    logger.info(f"Dataset File: {output_file}")
    logger.info(f"Summary File: {summary_file}")
    logger.info("="*70)


if __name__ == "__main__":
    main()
