"""
Generate 10K-step dataset with BATCH PROCESSING (Memory Efficient)
Fixes: No duplicates + Memory-efficient batch processing + Incremental save
"""

import logging
import sys
from pathlib import Path
import json
import random
import gc
import time
from PIL import Image
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_generation.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

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

# Configuration
BATCH_SIZE = 20  # Process 20 trajectories at a time (VERY memory efficient for low-end systems)
TARGET_STEPS = 7800  # Target total steps (matches available data)
OUTPUT_DIR = Path("output/dataset_10k_final")
IMAGES_DIR = OUTPUT_DIR / "images"
BATCH_FILES_DIR = OUTPUT_DIR / "batches"

def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot as compressed JPEG"""
    try:
        if image is None:
            return False
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Resize to 512px width for LOW MEMORY systems (maintaining aspect ratio)
        if image.width > 512:
            aspect_ratio = image.height / image.width
            new_width = 512
            new_height = int(new_width * aspect_ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # Save with 70% quality (smaller files)
        image.save(path, 'JPEG', quality=70, optimize=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to save screenshot {path}: {e}")
        return False

def serialize_step(step, task_idx: int, step_idx: int) -> dict:
    """Convert AugmentedStep to JSON-serializable dict with image saving"""
    # Get original step
    orig = step.original_step
    
    # Save screenshots (if they exist)
    state_before_path = IMAGES_DIR / f"task_{task_idx:04d}" / f"step_{step_idx:04d}_before.jpg"
    state_after_path = IMAGES_DIR / f"task_{task_idx:04d}" / f"step_{step_idx:04d}_after.jpg"
    
    if orig.state_before is not None:
        save_screenshot(orig.state_before, state_before_path)
    
    if orig.state_after is not None:
        save_screenshot(orig.state_after, state_after_path)
    
    # Build step dict
    step_dict = {
        'task_id': orig.task_id,
        'step_number': orig.step_number,
        'action_type': orig.action_type,
        'action_target': orig.action_target,
        'action_coords': list(orig.action_coords) if orig.action_coords else None,
        'execution_outcome': step.execution_outcome,
        'is_augmented': step.is_augmented,
        
        # Failure metadata
        'injection_type': step.injection_type if step.is_augmented else None,
        'failure_type': step.failure_type if step.is_augmented else None,
        'failure_subtype': step.failure_subtype if step.is_augmented else None,
        'root_cause': step.root_cause if step.is_augmented else None,
        
        # Recovery metadata
        'recovery_strategy': step.recovery_strategy if step.is_augmented else None,
        'recovery_action': step.recovery_action if step.is_augmented else None,
        'recovery_success': step.recovery_success if step.is_augmented else False,
        
        # Image paths
        'state_before_image': f"images/task_{task_idx:04d}/step_{step_idx:04d}_before.jpg",
        'state_after_image': f"images/task_{task_idx:04d}/step_{step_idx:04d}_after.jpg"
    }
    
    return step_dict

def process_batch(loader, pipeline, batch_num: int, annotation_ids: List[str], global_task_offset: int):
    """
    Process one batch of trajectories (MEMORY EFFICIENT)
    
    Args:
        loader: Data loader
        pipeline: Injection pipeline
        batch_num: Batch number for logging
        annotation_ids: List of annotation IDs to load for this batch
        global_task_offset: Starting task index for file naming
    
    Returns:
        Batch statistics dict
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"BATCH {batch_num} - {len(annotation_ids)} trajectories")
    logger.info(f"{'='*70}")
    
    # Load ONLY this batch's trajectories by ID (memory efficient!)
    logger.info(f"Loading {len(annotation_ids)} trajectories...")
    batch_trajs = loader.load_trajectories(
        split='train',
        filter_by_ids=annotation_ids,  # ONLY load these specific IDs!
        load_screenshots=True
    )
    logger.info(f"Loaded {len(batch_trajs)} trajectories for this batch")
    
    # Process with failure injection
    logger.info("Injecting failures...")
    augmented = []
    failed_count = 0
    
    for i, traj in enumerate(batch_trajs):
        try:
            aug_traj = pipeline.augment_trajectory(traj)
            augmented.append(aug_traj)
            
            # Free original trajectory immediately
            del traj
            
            # More frequent progress updates for smaller batches
            if (i + 1) % 5 == 0:
                logger.info(f"  Processed {i + 1}/{len(batch_trajs)} trajectories...")
                # Aggressive memory cleanup every 5 trajectories
                gc.collect()
        except Exception as e:
            failed_count += 1
            if failed_count <= 3:
                logger.error(f"  Failed trajectory {i}: {type(e).__name__}: {e}")
    
    # Final cleanup
    del batch_trajs
    gc.collect()
    
    logger.info(f"Generated {len(augmented)} augmented trajectories")
    
    # Serialize and save this batch
    logger.info("Saving batch...")
    batch_data = []
    batch_stats = {
        'total_steps': 0,
        'clean_steps': 0,
        'augmented_steps': 0,
        'failure_counts': {}
    }
    
    for traj_idx, traj in enumerate(augmented):
        global_idx = global_task_offset + traj_idx
        orig_traj = traj.original_trajectory
        
        steps_data = []
        for step_idx, step in enumerate(traj.augmented_steps):
            step_dict = serialize_step(step, global_idx, step_idx)
            steps_data.append(step_dict)
            
            # Count statistics
            batch_stats['total_steps'] += 1
            if step.is_augmented:
                batch_stats['augmented_steps'] += 1
                failure_type = step.injection_type
                if failure_type:
                    batch_stats['failure_counts'][failure_type] = \
                        batch_stats['failure_counts'].get(failure_type, 0) + 1
            else:
                batch_stats['clean_steps'] += 1
        
        batch_data.append({
            'task_id': orig_traj.task_id,
            'website': orig_traj.website if hasattr(orig_traj, 'website') else None,
            'domain': orig_traj.domain if hasattr(orig_traj, 'domain') else None,
            'steps': steps_data
        })
    
    # Save batch file
    batch_file = BATCH_FILES_DIR / f"batch_{batch_num:03d}.json"
    batch_file.parent.mkdir(parents=True, exist_ok=True)
    with open(batch_file, 'w', encoding='utf-8') as f:
        json.dump(batch_data, f, indent=2)
    
    logger.info(f"Batch saved to {batch_file}")
    logger.info(f"  Steps in batch: {batch_stats['total_steps']}")
    logger.info(f"  Augmented: {batch_stats['augmented_steps']} ({batch_stats['augmented_steps']/batch_stats['total_steps']*100:.1f}%)")
    
    # Aggressive cleanup of batch memory
    del augmented, batch_data
    gc.collect()
    
    return batch_stats

def merge_batches():
    """Merge all batch files into final dataset"""
    logger.info("\n" + "="*70)
    logger.info("MERGING BATCHES")
    logger.info("="*70)
    
    batch_files = sorted(BATCH_FILES_DIR.glob("batch_*.json"))
    logger.info(f"Found {len(batch_files)} batch files")
    
    all_data = []
    total_stats = {
        'total_steps': 0,
        'clean_steps': 0,
        'augmented_steps': 0,
        'failure_counts': {}
    }
    
    for batch_file in batch_files:
        logger.info(f"  Merging {batch_file.name}...")
        with open(batch_file, 'r') as f:
            batch_data = json.load(f)
            all_data.extend(batch_data)
            
            # Aggregate statistics
            for traj in batch_data:
                for step in traj['steps']:
                    total_stats['total_steps'] += 1
                    if step['is_augmented']:
                        total_stats['augmented_steps'] += 1
                        ft = step['injection_type']
                        if ft:
                            total_stats['failure_counts'][ft] = \
                                total_stats['failure_counts'].get(ft, 0) + 1
                    else:
                        total_stats['clean_steps'] += 1
    
    # Save final dataset
    output_file = OUTPUT_DIR / "augmented_trajectories.json"
    logger.info(f"\nSaving final dataset to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)
    
    # Save summary
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(total_stats, f, indent=2)
    
    logger.info(f"Dataset saved: {len(all_data)} trajectories, {total_stats['total_steps']} steps")
    
    # Cleanup batch files
    logger.info("\nCleaning up batch files...")
    for batch_file in batch_files:
        batch_file.unlink()
    
    return total_stats

def main():
    """Main execution"""
    logger.info("\n" + "="*70)
    logger.info("MEMORY-EFFICIENT BATCH GENERATION")
    logger.info("="*70)
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize loader
    logger.info("\nLoading Mind2Web dataset...")
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False
    )
    loader.load_from_cache()
    logger.info("Dataset loaded")
    
    # Load ALL annotation IDs (metadata only - NO SCREENSHOTS YET!)
    logger.info("\nLoading trajectory IDs (metadata only)...")
    all_trajs_metadata = loader.load_trajectories(
        split='train',
        limit=None,
        load_screenshots=False  # Just IDs, no images!
    )
    
    all_annotation_ids = [t.task_id for t in all_trajs_metadata]
    logger.info(f"Found {len(all_annotation_ids)} unique trajectories")
    
    # Shuffle to randomize (NO DUPLICATES!)
    random.shuffle(all_annotation_ids)
    logger.info(f"Shuffled {len(all_annotation_ids)} IDs")
    
    # Free metadata
    del all_trajs_metadata
    gc.collect()
    
    # Initialize injection pipeline
    logger.info("\nInitializing failure injection pipeline...")
    config = InjectionConfig(
        injection_rate=0.60,
        failure_type_distribution={
            "TARGET_MISSING": 0.30,
            "MISCLICK": 0.25,
            "WRONG_OPERATION": 0.20,
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
    
    logger.info("Pipeline initialized with 5 failure injectors")
    
    # Process in batches (memory efficient)
    logger.info("\n" + "="*70)
    logger.info("PROCESSING IN BATCHES")
    logger.info("="*70)
    
    total_steps_so_far = 0
    global_task_offset = 0
    batch_num = 0
    
    for i in range(0, len(all_annotation_ids), BATCH_SIZE):
        # Check if we have enough steps
        if total_steps_so_far >= TARGET_STEPS:
            logger.info(f"\n✅ Reached target: {total_steps_so_far} steps")
            break
        
        batch_num += 1
        batch_ids = all_annotation_ids[i:i+BATCH_SIZE]
        
        try:
            stats = process_batch(loader, pipeline, batch_num, batch_ids, global_task_offset)
            total_steps_so_far += stats['total_steps']
            global_task_offset += len(batch_ids)
            
            logger.info(f"\n✅ Batch {batch_num} complete. Total steps so far: {total_steps_so_far}/{TARGET_STEPS}")
            
            # Give system time to cleanup memory between batches
            time.sleep(2)
            gc.collect()
            
        except Exception as e:
            logger.error(f"❌ Batch {batch_num} failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("Continuing with next batch...")
    
    # Merge all batches
    logger.info("\n" + "="*70)
    logger.info("MERGING BATCHES")
    logger.info("="*70)
    final_stats = merge_batches()
    
    # Display final statistics
    logger.info("\n" + "="*70)
    logger.info("GENERATION COMPLETE!")
    logger.info("="*70)
    logger.info(f"\nTotal Steps: {final_stats['total_steps']}")
    logger.info(f"Clean Steps: {final_stats['clean_steps']} ({final_stats['clean_steps']/final_stats['total_steps']*100:.1f}%)")
    logger.info(f"Augmented Steps: {final_stats['augmented_steps']} ({final_stats['augmented_steps']/final_stats['total_steps']*100:.1f}%)")
    logger.info(f"\nFailure Distribution:")
    for ft, count in sorted(final_stats['failure_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = count / final_stats['augmented_steps'] * 100 if final_stats['augmented_steps'] > 0 else 0
        logger.info(f"  {ft}: {count} ({pct:.1f}%)")
    
    # Quality gates
    logger.info("\n" + "="*70)
    logger.info("QUALITY GATES")
    logger.info("="*70)
    
    aug_rate = final_stats['augmented_steps'] / final_stats['total_steps'] * 100
    loop_count = final_stats['failure_counts'].get('LOOP', 0)
    loop_pct = loop_count / final_stats['augmented_steps'] * 100 if final_stats['augmented_steps'] > 0 else 0
    num_types = len(final_stats['failure_counts'])
    
    logger.info(f"  [{'PASS' if 40 <= aug_rate <= 70 else 'FAIL'}] Augmentation Rate: {aug_rate:.1f}% (target: 40-70%)")
    logger.info(f"  [{'PASS' if loop_pct >= 5 else 'FAIL'}] LOOP Failures: {loop_count} ({loop_pct:.1f}%, threshold: >=5%)")
    logger.info(f"  [{'PASS' if num_types == 5 else 'FAIL'}] All Failure Types: {num_types}/5 present")
    
    logger.info("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nGeneration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
