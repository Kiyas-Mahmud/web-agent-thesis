"""
Generate 10K-step dataset with NO DUPLICATES
Fixed approach: Load all trajectories once, then process until 10K steps
"""

import logging
import sys
from pathlib import Path
import json
import random
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
TARGET_STEPS = 7800  # Adjusted to available data (7,775 total)
BATCH_SIZE = 50  # Process 50 trajectories at a time (for memory safety)
OUTPUT_DIR = Path("output/dataset_10k_final")
IMAGES_DIR = OUTPUT_DIR / "images"
RANDOM_SEED = 42  # For reproducibility

def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot as compressed JPEG with optimal size"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Resize to 768px width (maintain aspect ratio)
        width, height = image.size
        if width > 768:
            new_width = 768
            new_height = int(height * (768 / width))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save as JPEG with 75% quality
        image.convert('RGB').save(path, 'JPEG', quality=75, optimize=True)
        return True
    except Exception as e:
        logger.error(f"Failed to save screenshot to {path}: {e}")
        return False

def serialize_step(step, task_idx: int, step_idx: int) -> dict:
    """Convert AugmentedStep to JSON-serializable dict with image saving"""
    # Save screenshots (if they exist)
    state_before_path = IMAGES_DIR / f"task_{task_idx:04d}" / f"step_{step_idx:04d}_before.jpg"
    state_after_path = IMAGES_DIR / f"task_{task_idx:04d}" / f"step_{step_idx:04d}_after.jpg"
    
    # Get original step
    orig = step.original_step
    
    # Save screenshots from original step (state_before/after ARE the PIL Images directly)
    if orig.state_before is not None:
        save_screenshot(orig.state_before, state_before_path)
    
    if orig.state_after is not None:
        save_screenshot(orig.state_after, state_after_path)
    
    # Build step dict - get action data from original_step
    step_dict = {
        'task_id': orig.task_id,
        'step_number': orig.step_number,
        'action_type': orig.action_type,
        'action_target': orig.action_target,
        'action_coords': list(orig.action_coords) if orig.action_coords else None,
        'execution_outcome': step.execution_outcome,
        'is_augmented': step.is_augmented,
        
        # Failure metadata (from AugmentedStep)
        'injection_type': step.injection_type if step.is_augmented else None,
        'failure_type': step.failure_type if step.is_augmented else None,
        'failure_subtype': step.failure_subtype if step.is_augmented else None,
        'root_cause': step.root_cause if step.is_augmented else None,
        
        # Recovery metadata (from AugmentedStep)
        'recovery_strategy': step.recovery_strategy if step.is_augmented else None,
        'recovery_action': step.recovery_action if step.is_augmented else None,
        'recovery_success': step.recovery_success if step.is_augmented else False,
        
        # Image paths (relative to OUTPUT_DIR)
        'state_before_image': f"images/task_{task_idx:04d}/step_{step_idx:04d}_before.jpg",
        'state_after_image': f"images/task_{task_idx:04d}/step_{step_idx:04d}_after.jpg"
    }
    
    return step_dict

def filter_valid_trajectories(trajectories: List) -> List:
    """Filter out trajectories with null/bad data - LENIENT"""
    valid = []
    for traj in trajectories:
        # Very basic check: trajectory exists and has steps
        if traj and hasattr(traj, 'steps') and traj.steps and len(traj.steps) > 0:
            valid.append(traj)
    
    logger.info(f"Filtered: {len(valid)}/{len(trajectories)} trajectories have valid data")
    return valid

def main():
    logger.info("="*70)
    logger.info("10K DATASET GENERATION - NO DUPLICATES")
    logger.info("="*70)
    
    # Set random seed
    random.seed(RANDOM_SEED)
    
    # Load dataset
    logger.info("\nLoading Mind2Web dataset...")
    loader = MultimodalMind2WebLoader(use_streaming=False)
    loader.download_dataset()
    logger.info("Dataset loaded")
    
    # Load ALL trajectories at once (WITH screenshots - they ARE in cache!)
    logger.info("\nLoading ALL available trajectories...")
    all_trajectories = loader.load_trajectories(
        split='train',
        limit=None,  # Load ALL
        load_screenshots=True  # Screenshots exist in cache
    )
    logger.info(f"Loaded {len(all_trajectories)} total trajectories")
    
    # Simple validation - just check trajectory has steps
    valid_trajectories = [t for t in all_trajectories if t and hasattr(t, 'steps') and len(t.steps) > 0]
    logger.info(f"Valid trajectories: {len(valid_trajectories)}/{len(all_trajectories)}")
    
    # Shuffle for randomness
    random.shuffle(valid_trajectories)
    logger.info(f"Shuffled {len(valid_trajectories)} valid trajectories")
    
    # Check if we have enough data
    total_available_steps = sum(len(t.steps) for t in valid_trajectories)
    logger.info(f"Total available steps: {total_available_steps}")
    
    if total_available_steps < TARGET_STEPS:
        logger.warning(f"Only {total_available_steps} steps available, target is {TARGET_STEPS}")
        logger.warning("Will generate maximum available data")
    
    # Initialize failure injection pipeline
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
    
    # Register all 5 failure injectors
    pipeline.register_injector(TargetMissingInjector(config))
    pipeline.register_injector(MisclickInjector(config))
    pipeline.register_injector(WrongOperationInjector(config))
    pipeline.register_injector(NoStateChangeInjector(config))
    pipeline.register_injector(LoopInjector(config))
    
    logger.info("Pipeline initialized with 5 failure injectors")
    
    # Process trajectories until we reach 10K steps
    logger.info("\n" + "="*70)
    logger.info("PROCESSING TRAJECTORIES")
    logger.info("="*70)
    
    all_augmented = []
    total_steps_processed = 0
    trajectories_processed = 0
    failed_count = 0
    
    for i in range(0, len(valid_trajectories), BATCH_SIZE):
        # Check if we've reached target
        if total_steps_processed >= TARGET_STEPS:
            logger.info(f"\nReached target: {total_steps_processed} steps")
            break
        
        batch = valid_trajectories[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        logger.info(f"\nProcessing batch {batch_num} ({len(batch)} trajectories)...")
        
        for traj in batch:
            try:
                # Augment trajectory
                aug_traj = pipeline.augment_trajectory(traj)
                all_augmented.append(aug_traj)
                
                # Count steps
                steps_in_traj = len(aug_traj.augmented_steps)
                total_steps_processed += steps_in_traj
                trajectories_processed += 1
                
                if trajectories_processed % 50 == 0:
                    logger.info(f"  Progress: {trajectories_processed} trajectories, {total_steps_processed} steps")
                
                # Check if we've reached target
                if total_steps_processed >= TARGET_STEPS:
                    logger.info(f"  Reached {total_steps_processed} steps - stopping")
                    break
                    
            except Exception as e:
                failed_count += 1
                # Show detailed error for first few failures
                if failed_count <= 3:
                    logger.error(f"  Failed to process trajectory {failed_count}: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                elif failed_count % 100 == 0:
                    logger.warning(f"  {failed_count} failures so far...")
        
        # Memory cleanup after each batch
        import gc
        gc.collect()
        
        # Stop if we've reached target
        if total_steps_processed >= TARGET_STEPS:
            break
    
    logger.info(f"\nProcessing complete:")
    logger.info(f"  Trajectories processed: {trajectories_processed}")
    logger.info(f"  Total steps: {total_steps_processed}")
    logger.info(f"  Failed: {failed_count}")
    
    # Save dataset
    logger.info("\n" + "="*70)
    logger.info("SAVING DATASET")
    logger.info("="*70)
    
    dataset = []
    clean_steps = 0
    augmented_steps = 0
    failure_counts = {}
    
    logger.info("\nSerializing trajectories and saving images...")
    
    for traj_idx, traj in enumerate(all_augmented):
        orig_traj = traj.original_trajectory
        
        steps_data = []
        for step_idx, step in enumerate(traj.augmented_steps):
            step_dict = serialize_step(step, traj_idx, step_idx)
            steps_data.append(step_dict)
            
            # Count statistics
            if step.is_augmented:
                augmented_steps += 1
                failure_type = step.injection_type
                if failure_type:
                    failure_counts[failure_type] = failure_counts.get(failure_type, 0) + 1
            else:
                clean_steps += 1
        
        dataset.append({
            'task_id': orig_traj.task_id,
            'website': orig_traj.website if hasattr(orig_traj, 'website') else None,
            'domain': orig_traj.domain if hasattr(orig_traj, 'domain') else None,
            'steps': steps_data
        })
        
        if (traj_idx + 1) % 100 == 0:
            logger.info(f"  Serialized {traj_idx + 1}/{len(all_augmented)} trajectories...")
    
    # Save trajectories JSON
    output_file = OUTPUT_DIR / "augmented_trajectories.json"
    logger.info(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    logger.info("Trajectories saved")
    
    # Save summary
    summary = {
        'total_trajectories': len(dataset),
        'total_steps': clean_steps + augmented_steps,
        'clean_steps': clean_steps,
        'augmented_steps': augmented_steps,
        'avg_steps_per_trajectory': (clean_steps + augmented_steps) / len(dataset) if dataset else 0,
        'failure_distribution': failure_counts,
        'failed_trajectories': failed_count,
        'generation_config': {
            'target_steps': TARGET_STEPS,
            'injection_rate': 0.60,
            'random_seed': RANDOM_SEED
        }
    }
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Summary saved to {summary_file}")
    
    # Display final statistics
    logger.info("\n" + "="*70)
    logger.info("GENERATION COMPLETE!")
    logger.info("="*70)
    logger.info(f"\nTotal Trajectories: {summary['total_trajectories']}")
    logger.info(f"Total Steps: {summary['total_steps']}")
    
    total_steps = clean_steps + augmented_steps
    if total_steps > 0:
        logger.info(f"Clean Steps: {clean_steps} ({clean_steps/total_steps*100:.1f}%)")
        logger.info(f"Augmented Steps: {augmented_steps} ({augmented_steps/total_steps*100:.1f}%)")
    else:
        logger.error("No steps were generated!")
        logger.error("This might be due to:")
        logger.error("  1. No valid trajectories found")
        logger.error("  2. All trajectories failed to process")
        logger.error("  3. Screenshots not loading properly")
        return
    
    logger.info(f"\nFailure Distribution:")
    for ft, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
        pct = count / augmented_steps * 100 if augmented_steps > 0 else 0
        logger.info(f"  {ft}: {count} ({pct:.1f}%)")
    
    # Check quality gates
    logger.info("\n" + "="*70)
    logger.info("QUALITY GATES")
    logger.info("="*70)
    
    aug_rate = augmented_steps / total_steps * 100 if total_steps > 0 else 0
    gate1 = "PASS" if 40 <= aug_rate <= 70 else "FAIL"
    logger.info(f"  [{gate1}] Augmentation Rate: {aug_rate:.1f}% (target: 40-70%)")
    
    loop_count = failure_counts.get('LOOP', 0)
    loop_pct = loop_count / augmented_steps * 100 if augmented_steps > 0 else 0
    gate2 = "PASS" if loop_pct >= 5.0 else "FAIL"
    logger.info(f"  [{gate2}] LOOP Failures: {loop_count} ({loop_pct:.1f}%, threshold: >=5%)")
    
    gate3 = "PASS" if len(failure_counts) == 5 else "FAIL"
    logger.info(f"  [{gate3}] All Failure Types: {len(failure_counts)}/5 present")
    
    # Check for duplicates
    unique_task_ids = set(t['task_id'] for t in dataset)
    gate4 = "PASS" if len(unique_task_ids) == len(dataset) else "FAIL"
    logger.info(f"  [{gate4}] No Duplicates: {len(unique_task_ids)} unique / {len(dataset)} total")
    
    logger.info("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nGeneration interrupted by user")
        logger.info("Partial results may be saved")
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}", exc_info=True)
        sys.exit(1)
