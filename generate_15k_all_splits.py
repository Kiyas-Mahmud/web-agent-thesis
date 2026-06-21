"""
Generate 15K+ dataset using ALL Mind2Web splits (train + test)

Strategy:
- Load ALL splits: train, test_domain, test_task, test_website
- Process in batches to avoid memory issues
- Keep current augmentation rate (~60%)
- Expected output: ~14K clean steps → ~22K total with augmentation
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
from src.offline_augmentation.injector_registry import InjectorRegistry
from src.offline_augmentation.augmentation_pipeline import OfflineAugmentationPipeline
from src.offline_augmentation.injectors.wrong_operation_injector import WrongOperationInjector
from src.offline_augmentation.injectors.no_state_change_injector import NoStateChangeInjector
from src.offline_augmentation.injectors.target_missing_injector import TargetMissingInjector
from src.offline_augmentation.injectors.misclick_injector import MisclickInjector
from src.offline_augmentation.injectors.loop_injector import LOOPInjector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_generation_15k.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = Path("output/dataset_15k_final")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_FILES_DIR = OUTPUT_DIR / "batches"
BATCH_SIZE = 20  # Process 20 trajectories at a time (memory-efficient for 16GB RAM)
TARGET_STEPS = 15000

# Image settings (memory-optimized)
IMAGE_WIDTH = 512  # Reduced from 768 for memory
IMAGE_QUALITY = 70  # Reduced from 75

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

def serialize_step(step, task_idx: int, step_idx: int, images_dir: Path) -> dict:
    """Serialize a step to JSON-compatible dict with image saving."""
    task_dir = images_dir / f"task_{task_idx:04d}"
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Save screenshots if available
    before_path = task_dir / f"step_{step_idx:04d}_before.jpg"
    after_path = task_dir / f"step_{step_idx:04d}_after.jpg"
    
    before_saved = False
    after_saved = False
    
    if hasattr(step, 'original_step') and step.original_step:
        # Augmented step
        orig = step.original_step
        if hasattr(orig, 'state_before') and orig.state_before:
            before_saved = save_screenshot(orig.state_before, before_path)
        if hasattr(orig, 'state_after') and orig.state_after:
            after_saved = save_screenshot(orig.state_after, after_path)
    else:
        # Clean step
        if hasattr(step, 'state_before') and step.state_before:
            before_saved = save_screenshot(step.state_before, before_path)
        if hasattr(step, 'state_after') and step.state_after:
            after_saved = save_screenshot(step.state_after, after_path)
    
    # Build serializable dict
    return {
        'task_id': step.task_id,
        'annotation_id': step.annotation_id,
        'action_type': step.action_type,
        'action_target': step.action_target,
        'action_target_bbox': step.action_target_bbox,
        'state_before_path': str(before_path.relative_to(images_dir.parent)) if before_saved else None,
        'state_after_path': str(after_path.relative_to(images_dir.parent)) if after_saved else None,
        'is_augmented': step.is_augmented,
        'injection_type': step.injection_type if step.is_augmented else None,
        'failure_reason': step.failure_reason if step.is_augmented else None,
        'recovery_action': step.recovery_action if step.is_augmented else None,
    }

def process_batch(
    loader: MultimodalMind2WebLoader,
    pipeline: OfflineAugmentationPipeline,
    annotation_ids: list,
    split: str,
    batch_idx: int,
    images_dir: Path
) -> dict:
    """Process a batch of trajectories."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Processing Batch {batch_idx} ({split.upper()}) - {len(annotation_ids)} trajectories")
    logger.info(f"{'='*70}")
    
    try:
        # Load ONLY this batch's trajectories WITH screenshots
        logger.info(f"Loading batch trajectories from {split} split...")
        trajectories = loader.load_trajectories(
            split=split,
            filter_by_ids=annotation_ids,
            load_screenshots=True  # THIS IS KEY - we need images!
        )
        logger.info(f"Loaded {len(trajectories)} trajectories")
        
        # Process each trajectory
        batch_steps = []
        clean_steps = 0
        augmented_steps = 0
        failure_counts = Counter()
        
        for traj_idx, traj in enumerate(trajectories):
            logger.info(f"  Processing trajectory {traj_idx+1}/{len(trajectories)}: {traj.task_id}")
            
            # Augment trajectory
            augmented_traj = pipeline.augment_trajectory(traj)
            
            # Serialize steps
            for step_idx, step in enumerate(augmented_traj.steps):
                serialized = serialize_step(
                    step,
                    task_idx=batch_idx * BATCH_SIZE + traj_idx,
                    step_idx=step_idx,
                    images_dir=images_dir
                )
                batch_steps.append(serialized)
                
                if step.is_augmented:
                    augmented_steps += 1
                    if step.injection_type:
                        failure_counts[step.injection_type] += 1
                else:
                    clean_steps += 1
            
            # Aggressive memory cleanup PER trajectory
            del augmented_traj
            del traj
            
            if (traj_idx + 1) % 5 == 0:
                gc.collect()
        
        # Final cleanup for batch
        del trajectories
        gc.collect()
        
        logger.info(f"Batch {batch_idx} complete:")
        logger.info(f"  Clean steps: {clean_steps}")
        logger.info(f"  Augmented steps: {augmented_steps}")
        logger.info(f"  Failure distribution: {dict(failure_counts)}")
        
        return {
            'batch_idx': batch_idx,
            'split': split,
            'steps': batch_steps,
            'clean_steps': clean_steps,
            'augmented_steps': augmented_steps,
            'failure_counts': dict(failure_counts)
        }
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_idx}: {e}")
        import traceback
        traceback.print_exc()
        return None

def merge_batches(batch_files_dir: Path, output_file: Path) -> dict:
    """Merge all batch files into final dataset."""
    logger.info("\n" + "="*70)
    logger.info("MERGING BATCHES")
    logger.info("="*70)
    
    all_trajectories = {}
    total_clean = 0
    total_augmented = 0
    total_failures = Counter()
    
    batch_files = sorted(batch_files_dir.glob("batch_*.json"))
    logger.info(f"Found {len(batch_files)} batch files")
    
    for batch_file in batch_files:
        logger.info(f"Loading {batch_file.name}...")
        with open(batch_file, 'r') as f:
            batch = json.load(f)
        
        total_clean += batch['clean_steps']
        total_augmented += batch['augmented_steps']
        
        for failure_type, count in batch['failure_counts'].items():
            total_failures[failure_type] += count
        
        # Group steps by trajectory
        for step in batch['steps']:
            task_id = step['task_id']
            if task_id not in all_trajectories:
                all_trajectories[task_id] = {
                    'task_id': task_id,
                    'annotation_id': step['annotation_id'],
                    'steps': []
                }
            all_trajectories[task_id]['steps'].append(step)
    
    # Convert to list
    final_trajectories = list(all_trajectories.values())
    total_steps = total_clean + total_augmented
    
    logger.info(f"\nMerge complete:")
    logger.info(f"  Total trajectories: {len(final_trajectories)}")
    logger.info(f"  Total steps: {total_steps}")
    logger.info(f"  Clean steps: {total_clean}")
    logger.info(f"  Augmented steps: {total_augmented}")
    
    # Save final dataset
    logger.info(f"\nSaving final dataset to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(final_trajectories, f, indent=2)
    
    return {
        'total_steps': total_steps,
        'clean_steps': total_clean,
        'augmented_steps': total_augmented,
        'failure_counts': dict(total_failures)
    }

def main():
    logger.info("\n" + "="*70)
    logger.info("15K DATASET GENERATION - ALL SPLITS")
    logger.info("="*70)
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize loader
    logger.info("\nInitializing Mind2Web dataset loader...")
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False
    )
    
    # Use download_dataset() to load ALL splits (will use cache, won't re-download)
    logger.info("\nLoading dataset from cache (all splits)...")
    success = loader.download_dataset()
    
    if not success:
        logger.error("Failed to load dataset!")
        return
    
    logger.info(f"Available splits: {list(loader.dataset.keys())}")
    
    # Load trajectory IDs from ALL splits
    all_splits = ['train', 'test_domain', 'test_task', 'test_website']
    all_annotation_ids = []
    split_ids = {}
    
    logger.info("\nLoading trajectory IDs from all splits (metadata only)...")
    for split in all_splits:
        try:
            logger.info(f"  Loading {split}...")
            trajs = loader.load_trajectories(
                split=split,
                limit=None,
                load_screenshots=False
            )
            ids = [t.task_id for t in trajs]
            split_ids[split] = ids
            all_annotation_ids.extend(ids)
            logger.info(f"    ✅ {split}: {len(ids)} trajectories")
        except Exception as e:
            logger.warning(f"    ⚠️ {split}: Not available ({e})")
    
    logger.info(f"\nTotal trajectories across all splits: {len(all_annotation_ids)}")
    
    # Shuffle for randomness
    random.seed(42)
    random.shuffle(all_annotation_ids)
    
    logger.info(f"Target steps: {TARGET_STEPS}")
    logger.info(f"Batch size: {BATCH_SIZE} trajectories")
    logger.info(f"Estimated batches: {len(all_annotation_ids) // BATCH_SIZE + 1}")
    
    # Setup augmentation pipeline
    logger.info("\nSetting up augmentation pipeline...")
    registry = InjectorRegistry()
    
    # Register all injectors
    registry.register(WrongOperationInjector())
    registry.register(NoStateChangeInjector())
    registry.register(TargetMissingInjector())
    registry.register(MisclickInjector())
    registry.register(LOOPInjector())
    
    pipeline = OfflineAugmentationPipeline(registry)
    logger.info(f"Registered {len(registry.list_injectors())} failure injectors")
    
    # Process in batches
    logger.info("\n" + "="*70)
    logger.info("STARTING BATCH PROCESSING")
    logger.info("="*70)
    
    batch_idx = 0
    processed_steps = 0
    
    for split in all_splits:
        if split not in split_ids:
            continue
            
        split_annotation_ids = split_ids[split]
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING {split.upper()} SPLIT - {len(split_annotation_ids)} trajectories")
        logger.info(f"{'='*70}")
        
        # Process split in batches
        for i in range(0, len(split_annotation_ids), BATCH_SIZE):
            batch_ids = split_annotation_ids[i:i+BATCH_SIZE]
            
            result = process_batch(
                loader=loader,
                pipeline=pipeline,
                annotation_ids=batch_ids,
                split=split,
                batch_idx=batch_idx,
                images_dir=IMAGES_DIR
            )
            
            if result:
                # Save batch
                batch_file = BATCH_FILES_DIR / f"batch_{batch_idx:04d}_{split}.json"
                with open(batch_file, 'w') as f:
                    json.dump(result, f)
                logger.info(f"✅ Batch {batch_idx} saved to {batch_file.name}")
                
                processed_steps += result['clean_steps'] + result['augmented_steps']
                logger.info(f"Progress: {processed_steps} steps generated")
                
                # Check if we've reached target
                if processed_steps >= TARGET_STEPS:
                    logger.info(f"\n🎯 TARGET REACHED: {processed_steps} >= {TARGET_STEPS}")
                    break
            
            batch_idx += 1
            
            # Brief delay between batches
            time.sleep(2)
        
        # Check if we've reached target
        if processed_steps >= TARGET_STEPS:
            break
    
    # Merge all batches
    logger.info("\n" + "="*70)
    logger.info("MERGING BATCHES INTO FINAL DATASET")
    logger.info("="*70)
    
    summary = merge_batches(
        batch_files_dir=BATCH_FILES_DIR,
        output_file=OUTPUT_DIR / "augmented_trajectories.json"
    )
    
    # Save summary
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\n✅ Summary saved to {summary_file}")
    
    # Print final statistics
    logger.info("\n" + "="*70)
    logger.info("GENERATION COMPLETE!")
    logger.info("="*70)
    logger.info(f"Total Steps: {summary['total_steps']}")
    logger.info(f"Clean Steps: {summary['clean_steps']} ({summary['clean_steps']/summary['total_steps']*100:.1f}%)")
    logger.info(f"Augmented Steps: {summary['augmented_steps']} ({summary['augmented_steps']/summary['total_steps']*100:.1f}%)")
    logger.info(f"\nFailure Distribution:")
    for failure_type, count in sorted(summary['failure_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = count / summary['augmented_steps'] * 100 if summary['augmented_steps'] > 0 else 0
        logger.info(f"  - {failure_type}: {count} ({pct:.1f}%)")
    
    # Quality gates
    logger.info(f"\nQuality Gates:")
    aug_rate = summary['augmented_steps'] / summary['total_steps'] * 100
    loop_pct = summary['failure_counts'].get('LOOP', 0) / summary['augmented_steps'] * 100 if summary['augmented_steps'] > 0 else 0
    
    gates_passed = []
    gates_passed.append(40 <= aug_rate <= 70)
    gates_passed.append(loop_pct >= 5)
    gates_passed.append(len(summary['failure_counts']) == 5)
    
    logger.info(f"  [{'PASS' if gates_passed[0] else 'FAIL'}] Augmentation Rate: {aug_rate:.1f}% (target: 40-70%)")
    logger.info(f"  [{'PASS' if gates_passed[1] else 'FAIL'}] LOOP Failures: {loop_pct:.1f}% (threshold: ≥5%)")
    logger.info(f"  [{'PASS' if gates_passed[2] else 'FAIL'}] All Failure Types: {len(summary['failure_counts'])}/5")
    
    if all(gates_passed):
        logger.info(f"\n✅ ALL QUALITY GATES PASSED!")
    else:
        logger.warning(f"\n⚠️ Some quality gates failed")

if __name__ == "__main__":
    main()
