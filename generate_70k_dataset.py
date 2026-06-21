"""
Generate 70K+ dataset using ALL Mind2Web splits with multi-augmentation strategy

Strategy:
- Load ALL splits: train, test_domain, test_task, test_website  
- Apply 4 augmentations per step (multi-augmentation for diversity)
- Each step gets 4 different failure types applied
- Expected output: 14,193 clean × 5 (1 clean + 4 augmented) = ~70,965 steps
- Maintain quality balance with duplicate detection
"""

import json
import logging
import random
import time
from pathlib import Path
from collections import Counter
from PIL import Image
import gc
import hashlib

from src.offline_data import MultimodalMind2WebLoader
from src.failure_injection import (
    InjectionPipeline,
    InjectionConfig,
    TargetMissingInjector,
    MisclickInjector,
    WrongOperationInjector,
    NoStateChangeInjector,
    LoopInjector
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_generation_70k.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = Path("output/dataset_70k_final")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_FILES_DIR = OUTPUT_DIR / "batches"
BATCH_SIZE = 20  # Process 20 trajectories at a time (memory-efficient)
IMAGE_WIDTH = 512  # Reduced for memory optimization
IMAGE_QUALITY = 70  # JPEG quality

# All splits to process
SPLITS = ['train', 'test_domain', 'test_task', 'test_website']

# Set seed for reproducibility
random.seed(42)

def compute_step_hash(step) -> str:
    """Compute SHA-256 hash for duplicate detection"""
    # Use key identifiers to create unique hash
    hash_str = f"{step.task_id}_{step.annotation_id}_{step.action_type}_{step.action_target}"
    return hashlib.sha256(hash_str.encode()).hexdigest()[:16]

def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot with optimization."""
    try:
        if image is None:
            return False
            
        # Resize to target width while maintaining aspect ratio
        if image.width > IMAGE_WIDTH:
            ratio = IMAGE_WIDTH / image.width
            new_height = int(image.height * ratio)
            image = image.resize((IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # Save with reduced quality
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, "JPEG", quality=IMAGE_QUALITY, optimize=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to save screenshot {path}: {e}")
        return False

def serialize_step(step, task_idx: int, step_idx: int, images_dir: Path, global_step_counter: int) -> dict:
    """Serialize augmented step to JSON-compatible dict with image saving."""
    task_dir = images_dir / f"task_{task_idx:05d}"
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Use global counter for unique image naming
    before_path = task_dir / f"step_{global_step_counter:06d}_before.jpg"
    after_path = task_dir / f"step_{global_step_counter:06d}_after.jpg"
    
    # Get original step (AugmentedStep has original_step attribute)
    orig = step.original_step
    
    # Save screenshots from original step
    before_saved = False
    after_saved = False
    if orig.state_before is not None:
        before_saved = save_screenshot(orig.state_before, before_path)
    if orig.state_after is not None:
        after_saved = save_screenshot(orig.state_after, after_path)
    
    # Build serializable dict
    return {
        'step_id': global_step_counter,
        'task_id': orig.task_id,
        'step_number': orig.step_number,
        'action_type': orig.action_type,
        'action_target': orig.action_target,
        'action_coords': list(orig.action_coords) if orig.action_coords else None,
        'execution_outcome': step.execution_outcome,
        'state_before_path': str(before_path.relative_to(images_dir.parent)) if before_saved else None,
        'state_after_path': str(after_path.relative_to(images_dir.parent)) if after_saved else None,
        'is_augmented': step.is_augmented,
        'injection_type': step.injection_type if step.is_augmented else None,
        'failure_type': step.failure_type if step.is_augmented else None,
        'failure_subtype': step.failure_subtype if step.is_augmented else None,
        'root_cause': step.root_cause if step.is_augmented else None,
        'recovery_strategy': step.recovery_strategy if step.is_augmented else None,
        'recovery_action': step.recovery_action if step.is_augmented else None,
        'recovery_success': step.recovery_success if step.is_augmented else False,
    }

def apply_multi_augmentation(clean_step, injectors: list, num_augmentations: int = 4):

def process_split(
    loader: MultimodalMind2WebLoader,
    split: str,
    all_injectors: list,
    images_dir: Path,
    global_step_counter: int,
    seen_hashes: set,
    task_id_offset: int
) -> tuple:
    """Process a single split with multi-augmentation"""
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing Split: {split.upper()}")
    logger.info(f"{'='*70}")
    
    # Load trajectories WITH screenshots
    logger.info(f"Loading trajectories from {split} split...")
    trajectories = loader.load_trajectories(
        split=split,
        limit=None,
        load_screenshots=True
    )
    pipeline: InjectionPipeline,
    images_dir: Path,
    global_step_counter: int,
    seen_hashes: set,
    task_id_offset: int
) -> tuple:
    """Process a single split with failure injection"""
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing Split: {split.upper()}")
    logger.info(f"{'='*70}")
    
    # Load trajectories WITH screenshots
    logger.info(f"Loading trajectories from {split} split...")
    trajectories = loader.load_trajectories(
        split=split,
        limit=None,
        load_screenshots=True
    )
    logger.info(f"Loaded {len(trajectories)} trajectories")
    
    all_steps = []
    clean_count = 0
    augmented_count = 0
    failure_counts = Counter()
    duplicate_count = 0
    
    for traj_idx, traj in enumerate(trajectories):
        if (traj_idx + 1) % 50 == 0:
            logger.info(f"  Processing trajectory {traj_idx+1}/{len(trajectories)}...")
        
        task_idx = task_id_offset + traj_idx
        
        try:
            # Apply injection pipeline to trajectory
            aug_traj = pipeline.augment_trajectory(traj)
            
            # Serialize all steps (both clean and augmented)
            for step_idx, aug_step in enumerate(aug_traj.augmented_steps):
                # Check for duplicates using original step
                step_hash = compute_step_hash(aug_step.original_step)
                if step_hash in seen_hashes:
                    duplicate_count += 1
                    continue
                
                seen_hashes.add(step_hash)
                
                # Serialize step
                serialized = serialize_step(
                    aug_step, task_idx, step_idx, images_dir, global_step_counter
                )
                all_steps.append(serialized)
                global_step_counter += 1
                
                # Count clean vs augmented
                if aug_step.is_augmented:
                    augmented_count += 1
                    failure_counts[aug_step.injection_type] += 1
                else:
                    clean_count += 1
                    
        except Exception as e:
            logger.error(f"Failed to process trajectory {traj_idx}: {e}")
            continue
    logger.info(f"Strategy: Apply 4 augmentations per clean step")
    logger.info(f"Expected: ~14,193 clean + ~56,772 augmented = ~70,965 total")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("="*70)
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize loader
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False
    )
    loader.load_from_cache()
    
    # Initialize all injectors
    logger.info("\nInitializing failure injectors...")
    all_injectors = [
        TargetMissingInjector(),
        MisclickInjector(),
        WrongOperationInjector(),
        NoStateChangeInjector(),
        LOOPInjector()
    ]
    logger.info(f"Loaded {len(all_injectors)} injectors")
    
    # Global tracking
    all_dataset_steps = []
    global_step_counter = 0
    seen_hashes = set()
    task_id_offseinjection pipeline with HIGH injection rate (400% to reach 70k)
    logger.info("\nInitializing failure injection pipeline...")
    config = InjectionConfig(
        injection_rate=4.0,  # 400% = 4 augmented steps per clean step
        failure_type_distribution={
            "TARGET_MISSING": 0.30,
            "MISCLICK": 0.25,
            "WROpipeline=pipeline
            "NO_STATE_CHANGE": 0.15,
            "LOOP": 0.10
        }
    )
    
    pipeline = InjectionPipeline(config)
    pipeline.register_injector(TargetMissingInjector(config))
    pipeline.register_injector(MisclickInjector(config))
    pipeline.register_injector(WrongOperationInjector(config))
    pipeline.register_injector(NoStateChangeInjector(config))
    pipeline.register_injector(LoopInjector(config))
    
    logger.info(f"Pipeline initialized with injection_rate={config.injection_rate}
                all_injectors=all_injectors,
                images_dir=IMAGES_DIR,
                global_step_counter=global_step_counter,
                seen_hashes=seen_hashes,
                task_id_offset=task_id_offset
            )
            all_dataset_steps.extend(split_steps)
            
            # Save intermediate results
            split_file = BATCH_FILES_DIR / f"{split}_steps.json"
            with open(split_file, 'w') as f:
                json.dump(split_steps, f, indent=2)
            logger.info(f"Saved {len(split_steps)} steps to {split_file}")
            
        except Exception as e:
            logger.error(f"Failed to process {split}: {e}")
            continue
    
    elapsed_time = time.time() - start_time
    
    # Final statistics
    logger.info(f"\n{'='*70}")
    logger.info("FINAL DATASET STATISTICS")
    logger.info(f"{'='*70}")
    
    clean_steps = [s for s in all_dataset_steps if not s['is_augmented']]
    augmented_steps = [s for s in all_dataset_steps if s['is_augmented']]
    
    logger.info(f"Total steps: {len(all_dataset_steps):,}")
    logger.info(f"  Clean: {len(clean_steps):,} ({len(clean_steps)/len(all_dataset_steps)*100:.1f}%)")
    logger.info(f"  Augmented: {len(augmented_steps):,} ({len(augmented_steps)/len(all_dataset_steps)*100:.1f}%)")
    logger.info(f"Duplicates removed: {len(seen_hashes) - len(clean_steps)}")
    
    # Failure type distribution
    failure_dist = Counter([s['injection_type'] for s in augmented_steps])
    logger.info(f"\nFailure Distribution:")
    for failure_type, count in failure_dist.most_common():
        percentage = count / len(augmented_steps) * 100
        logger.info(f"  {failure_type}: {count:,} ({percentage:.1f}%)")
    
    # Save final dataset
    output_file = OUTPUT_DIR / "augmented_trajectories.json"
    logger.info(f"\nSaving final dataset to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(all_dataset_steps, f, indent=2)
    
    # Save summary
    summary = {
        'total_steps': len(all_dataset_steps),
        'clean_steps': len(clean_steps),
        'augmented_steps': len(augmented_steps),
        'failure_distribution': dict(failure_dist),
        'splits_processed': SPLITS,
        'duplicates_removed': len(seen_hashes) - len(clean_steps),
        'processing_time_seconds': elapsed_time,
        'output_directory': str(OUTPUT_DIR)
    }
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\n✅ Dataset generation complete!")
    logger.info(f"   Total steps: {len(all_dataset_steps):,}")
    logger.info(f"   Processing time: {elapsed_time/60:.1f} minutes")
    logger.info(f"   Output: {OUTPUT_DIR}")
    logger.info("="*70)

if __name__ == "__main__":
    main()
