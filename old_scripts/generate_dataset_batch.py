"""
Batch dataset generation - processes in small chunks to avoid memory issues.
Run this in a standalone PowerShell terminal (NOT in VS Code).
"""

import logging
import sys
from pathlib import Path
import json
import gc
from PIL import Image

# Setup logging WITHOUT emoji characters (Windows console compatibility)
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
BATCH_SIZE = 50  # Process 50 tasks at a time
TOTAL_TASKS = 1000  # Full dataset generation
OUTPUT_DIR = Path("output/dataset_1000_final")
IMAGES_DIR = OUTPUT_DIR / "images"

def save_screenshot(image: Image.Image, path: Path) -> bool:
    """Save screenshot as compressed JPEG with optimal size"""
    try:
        if image is None:
            return False
        
        # Resize to 768px width (maintaining aspect ratio)
        if image.width > 768:
            aspect_ratio = image.height / image.width
            new_width = 768
            new_height = int(new_width * aspect_ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # Save with 75% quality
        image.save(path, 'JPEG', quality=75, optimize=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to save screenshot {path}: {e}")
        return False

def serialize_step(step, task_images_dir: Path, step_idx: int):
    """Convert AugmentedStep to JSON-serializable dict"""
    data = {
        'is_augmented': step.is_augmented,
        'injection_type': step.injection_type,
        'recovery_strategy': step.recovery_strategy,
        'recovery_success': step.recovery_success,
        'failure_type': step.failure_type,
        'failure_subtype': step.failure_subtype,
        'root_cause': step.root_cause,
        'recovery_action': step.recovery_action if hasattr(step, 'recovery_action') else None,
        'execution_outcome': step.execution_outcome if hasattr(step, 'execution_outcome') else None
    }
    
    # Add original step info
    if hasattr(step, 'original_step'):
        orig_step = step.original_step
        data['action_type'] = orig_step.action_type
        data['step_number'] = orig_step.step_number
        data['task_id'] = orig_step.task_id
        data['action_target'] = orig_step.action_target
        data['action_coords'] = orig_step.action_coords
        
        # Save screenshots and add paths
        if orig_step.state_before is not None:
            before_path = task_images_dir / f"step_{step_idx:04d}_before.jpg"
            if save_screenshot(orig_step.state_before, before_path):
                data['state_before_image'] = f"images/{task_images_dir.name}/{before_path.name}"
        
        if orig_step.state_after is not None:
            after_path = task_images_dir / f"step_{step_idx:04d}_after.jpg"
            if save_screenshot(orig_step.state_after, after_path):
                data['state_after_image'] = f"images/{task_images_dir.name}/{after_path.name}"
    
    return data

def process_batch(loader, pipeline, batch_num, start_idx, batch_size):
    """Process one batch of trajectories"""
    logger.info(f"\n{'='*70}")
    logger.info(f"BATCH {batch_num} - Tasks {start_idx} to {start_idx + batch_size - 1}")
    logger.info(f"{'='*70}\n")
    
    # Load trajectories for this batch
    logger.info(f"Loading {batch_size} trajectories...")
    trajectories = loader.load_trajectories(
        split='train',
        limit=batch_size,
        load_screenshots=True
    )
    
    if not trajectories:
        logger.error("No trajectories loaded!")
        return None
    
    logger.info(f"OK Loaded {len(trajectories)} trajectories")
    
    # Process with failure injection
    logger.info("Injecting failures...")
    augmented = []
    for i, traj in enumerate(trajectories):
        try:
            aug_traj = pipeline.augment_trajectory(traj)
            augmented.append(aug_traj)
            
            if (i + 1) % 10 == 0:
                logger.info(f"  Processed {i + 1}/{len(trajectories)} trajectories...")
        except Exception as e:
            logger.warning(f"Failed to process trajectory {i}: {e}")
    
    logger.info(f"OK Generated {len(augmented)} augmented trajectories")
    
    # Save this batch
    logger.info("Saving batch...")
    batch_data = []
    
    for traj_idx, traj in enumerate(augmented):
        global_idx = start_idx + traj_idx
        orig_traj = traj.original_trajectory
        
        # Create task-specific images directory
        task_images_dir = IMAGES_DIR / f"task_{global_idx:04d}"
        task_images_dir.mkdir(parents=True, exist_ok=True)
        
        batch_data.append({
            'task_id': orig_traj.task_id,
            'domain': orig_traj.domain,
            'website': orig_traj.website,
            'confirmed_task': orig_traj.confirmed_task if hasattr(orig_traj, 'confirmed_task') else '',
            'num_steps': len(traj.augmented_steps),
            'num_augmented': sum(1 for s in traj.augmented_steps if s.is_augmented),
            'num_clean': sum(1 for s in traj.augmented_steps if not s.is_augmented),
            'steps': [serialize_step(s, task_images_dir, step_idx) 
                     for step_idx, s in enumerate(traj.augmented_steps)]
        })
    
    # Save batch file
    batch_file = OUTPUT_DIR / f"batch_{batch_num:03d}.json"
    with open(batch_file, 'w') as f:
        json.dump(batch_data, f, indent=2)
    
    logger.info(f"OK Saved batch to {batch_file}")
    
    # Collect statistics
    stats = pipeline.get_statistics()
    
    # Cleanup memory
    del trajectories
    del augmented
    gc.collect()
    
    return stats

def merge_batches():
    """Merge all batch files into final dataset"""
    logger.info("\n" + "="*70)
    logger.info("MERGING BATCHES INTO FINAL DATASET")
    logger.info("="*70 + "\n")
    
    batch_files = sorted(OUTPUT_DIR.glob("batch_*.json"))
    logger.info(f"Found {len(batch_files)} batch files")
    
    all_data = []
    total_stats = {
        'total_trajectories': 0,
        'total_steps': 0,
        'clean_steps': 0,
        'augmented_steps': 0,
        'failure_distribution': {}
    }
    
    for batch_file in batch_files:
        logger.info(f"  Merging {batch_file.name}...")
        with open(batch_file, 'r') as f:
            batch_data = json.load(f)
            all_data.extend(batch_data)
            
            # Update statistics
            for traj in batch_data:
                total_stats['total_trajectories'] += 1
                total_stats['total_steps'] += traj['num_steps']
                total_stats['clean_steps'] += traj['num_clean']
                total_stats['augmented_steps'] += traj['num_augmented']
                
                # Count failure types
                for step in traj['steps']:
                    if step['is_augmented'] and step['injection_type']:
                        ft = step['injection_type']
                        total_stats['failure_distribution'][ft] = \
                            total_stats['failure_distribution'].get(ft, 0) + 1
    
    # Save final merged file
    final_file = OUTPUT_DIR / "augmented_trajectories.json"
    logger.info(f"\nSaving final dataset to {final_file}...")
    with open(final_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    # Save summary
    total_stats['avg_steps_per_trajectory'] = (
        total_stats['total_steps'] / total_stats['total_trajectories']
        if total_stats['total_trajectories'] > 0 else 0
    )
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(total_stats, f, indent=2)
    
    logger.info(f"OK Final dataset saved!")
    logger.info(f"\nFinal Statistics:")
    logger.info(f"  Trajectories: {total_stats['total_trajectories']}")
    logger.info(f"  Total Steps: {total_stats['total_steps']}")
    
    if total_stats['total_steps'] > 0:
        logger.info(f"  Clean Steps: {total_stats['clean_steps']} ({total_stats['clean_steps']/total_stats['total_steps']*100:.1f}%)")
        logger.info(f"  Augmented Steps: {total_stats['augmented_steps']} ({total_stats['augmented_steps']/total_stats['total_steps']*100:.1f}%)")
        logger.info(f"\n  Failure Distribution:")
        for ft, count in sorted(total_stats['failure_distribution'].items(), key=lambda x: x[1], reverse=True):
            pct = count / total_stats['augmented_steps'] * 100 if total_stats['augmented_steps'] > 0 else 0
            logger.info(f"    {ft}: {count} ({pct:.1f}%)")
    else:
        logger.error("  ERROR: No trajectories were successfully processed!")
        logger.error("  Check the error messages above for details.")
    
    # Delete batch files
    logger.info("\nCleaning up batch files...")
    for batch_file in batch_files:
        batch_file.unlink()
    
    return total_stats

def main():
    """Main execution"""
    logger.info("\n" + "="*70)
    logger.info("BATCH DATASET GENERATION - 1,000 TASKS")
    logger.info("="*70 + "\n")
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize loader
    logger.info("Loading Mind2Web dataset...")
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False
    )
    loader.load_from_cache()
    logger.info("Dataset loaded")
    
    # Initialize injection pipeline
    logger.info("Initializing failure injection pipeline...")
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
    
    # Process in batches
    num_batches = (TOTAL_TASKS + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(1, num_batches + 1):
        start_idx = (batch_num - 1) * BATCH_SIZE
        remaining = TOTAL_TASKS - start_idx
        batch_size = min(BATCH_SIZE, remaining)
        
        try:
            stats = process_batch(loader, pipeline, batch_num, start_idx, batch_size)
            if stats:
                logger.info(f"OK Batch {batch_num}/{num_batches} complete")
        except Exception as e:
            logger.error(f"ERROR Batch {batch_num} failed: {e}")
            logger.info("Continuing with next batch...")
    
    # Merge all batches
    final_stats = merge_batches()
    
    logger.info("\n" + "="*70)
    logger.info("GENERATION COMPLETE!")
    logger.info("="*70)
    
    return final_stats

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nGeneration interrupted by user")
        logger.info("Partial results saved in batch files")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
