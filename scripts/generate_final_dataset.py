"""
Generate final dataset with batch processing to avoid memory issues.

NOTE: For 10K dataset generation, use the new generate_10k_dataset.py instead.
      This script is kept for custom batch processing scenarios.

Usage:
    python scripts/generate_final_dataset.py --num-tasks 1000 --batch-size 100
"""

import argparse
import logging
import sys
import json
import gc
from pathlib import Path
from collections import Counter
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        
        # Save with 75% quality (good balance)
        image.save(path, 'JPEG', quality=75, optimize=True)
        return True
    except Exception as e:
        logger.warning(f"Failed to save screenshot {path}: {e}")
        return False


def serialize_step(step, task_images_dir: Path, step_idx: int):
    """Convert AugmentedStep to JSON-serializable dict with image paths"""
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
                # Store relative path from output_dir
                data['state_before_image'] = f"images/{task_images_dir.name}/{before_path.name}"
        
        if orig_step.state_after is not None:
            after_path = task_images_dir / f"step_{step_idx:04d}_after.jpg"
            if save_screenshot(orig_step.state_after, after_path):
                # Store relative path from output_dir
                data['state_after_image'] = f"images/{task_images_dir.name}/{after_path.name}"
    
    return data


def process_batch(all_trajectories, pipeline, batch_start, batch_end, output_dir, images_dir, total_offset):
    """Process a batch of trajectories and save results"""
    logger.info(f"\n📦 Processing batch trajectories {batch_start}-{batch_end}...")
    
    # Get batch slice
    trajectories = all_trajectories[batch_start:batch_end]
    
    if not trajectories:
        return None, 0, 0, Counter()
    
    logger.info(f"   Processing {len(trajectories)} trajectories")
    
    # Process batch
    augmented_batch = []
    batch_clean_steps = 0
    batch_augmented_steps = 0
    batch_failure_counts = Counter()
    
    for idx, traj in enumerate(trajectories):
        try:
            aug_traj = pipeline.augment_trajectory(traj)
            augmented_batch.append(aug_traj)
            
            # Count stats for this trajectory
            for step in aug_traj.augmented_steps:
                if step.is_augmented:
                    batch_augmented_steps += 1
                    if hasattr(step, 'injection_type') and step.injection_type:
                        batch_failure_counts[step.injection_type] += 1
                else:
                    batch_clean_steps += 1
                    
        except Exception as e:
            logger.warning(f"      Failed to process trajectory: {e}")
    
    # Save batch results
    logger.info(f"   💾 Saving {len(augmented_batch)} trajectories...")
    
    batch_data = []
    for traj_idx, traj in enumerate(augmented_batch):
        orig_traj = traj.original_trajectory
        
        # Create task-specific images directory
        global_traj_idx = total_offset + traj_idx
        task_images_dir = images_dir / f"task_{global_traj_idx:04d}"
        task_images_dir.mkdir(exist_ok=True)
        
        batch_data.append({
            'task_id': orig_traj.task_id,
            'domain': orig_traj.domain,
            'website': orig_traj.website,
            'confirmed_task': orig_traj.confirmed_task if hasattr(orig_traj, 'confirmed_task') else '',
            'num_steps': len(traj.augmented_steps),
            'num_augmented': sum(1 for s in traj.augmented_steps if s.is_augmented),
            'num_clean': sum(1 for s in traj.augmented_steps if not s.is_augmented),
            'steps': [serialize_step(s, task_images_dir, step_idx) for step_idx, s in enumerate(traj.augmented_steps)]
        })
    
    logger.info(f"   ✅ Batch saved: {batch_clean_steps} clean, {batch_augmented_steps} augmented")
    
    # Clear memory
    del trajectories
    del augmented_batch
    gc.collect()
    
    return batch_data, batch_clean_steps, batch_augmented_steps, batch_failure_counts


def main():
    parser = argparse.ArgumentParser(description="Generate final dataset with batch processing")
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=1000,
        help="Total number of tasks to generate (default: 1000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of tasks per batch (default: 100)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/dataset_10k_final",
        help="Output directory for generated data"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("FINAL DATASET GENERATION (Batch Processing)")
    logger.info("=" * 80)
    logger.info(f"Target: {args.num_tasks} tasks")
    logger.info(f"Batch size: {args.batch_size} tasks")
    logger.info(f"Output: {args.output_dir}")
    
    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Load dataset
    logger.info("\n📥 Loading Mind2Web from cached parquet files...")
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
    loader.load_from_cache()
    
    # Load all trajectories (lightweight - no screenshots yet)
    logger.info(f"\n📦 Loading {args.num_tasks} trajectory structures...")
    all_trajectories = loader.load_trajectories(
        split='train',
        limit=args.num_tasks,
        load_screenshots=True  # Load screenshots for processing
    )
    logger.info(f"✅ Loaded {len(all_trajectories)} trajectories")
    
    # Initialize injection pipeline
    logger.info("\n🔧 Initializing failure injection pipeline...")
    config = InjectionConfig(injection_rate=0.6)
    pipeline = InjectionPipeline(config)
    
    pipeline.register_injector(TargetMissingInjector(config))
    pipeline.register_injector(MisclickInjector(config))
    pipeline.register_injector(WrongOperationInjector(config))
    pipeline.register_injector(NoStateChangeInjector(config))
    pipeline.register_injector(LoopInjector(config))
    
    logger.info("✅ Registered 5 failure injectors")
    
    # Process in batches
    all_data = []
    total_clean = 0
    total_augmented = 0
    total_failure_counts = Counter()
    
    num_batches = (len(all_trajectories) + args.batch_size - 1) // args.batch_size
    
    for batch_idx in range(num_batches):
        batch_start = batch_idx * args.batch_size
        batch_end = min(batch_start + args.batch_size, len(all_trajectories))
        
        logger.info(f"\n{'='*80}")
        logger.info(f"BATCH {batch_idx + 1}/{num_batches} (Tasks {batch_start + 1}-{batch_end})")
        logger.info(f"{'='*80}")
        
        batch_data, clean, augmented, failures = process_batch(
            all_trajectories, pipeline, batch_start, batch_end, output_dir, images_dir, len(all_data)
        )
        
        if batch_data is None:
            logger.warning(f"⚠️  Batch {batch_idx + 1} returned no data, stopping...")
            break
        
        all_data.extend(batch_data)
        total_clean += clean
        total_augmented += augmented
        total_failure_counts.update(failures)
        
        # Show progress
        progress = len(all_data) / len(all_trajectories) * 100
        logger.info(f"\n📊 Overall Progress: {len(all_data)}/{len(all_trajectories)} tasks ({progress:.1f}%)")
        logger.info(f"   Total steps: {total_clean + total_augmented}")
        logger.info(f"   Clean: {total_clean} ({total_clean/(total_clean+total_augmented)*100:.1f}%)")
        logger.info(f"   Augmented: {total_augmented} ({total_augmented/(total_clean+total_augmented)*100:.1f}%)")
    
    # Save final JSON
    logger.info(f"\n💾 Saving final JSON file...")
    json_file = output_dir / "augmented_trajectories.json"
    with open(json_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    logger.info(f"✅ Saved {len(all_data)} trajectories to {json_file}")
    
    # Save summary
    summary = {
        'total_trajectories': len(all_data),
        'total_steps': total_clean + total_augmented,
        'clean_steps': total_clean,
        'augmented_steps': total_augmented,
        'avg_steps_per_trajectory': (total_clean + total_augmented) / len(all_data) if all_data else 0,
        'failure_distribution': dict(total_failure_counts),
        'pipeline_statistics': pipeline.get_statistics()
    }
    
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"✅ Summary saved to {summary_file}")
    
    # Final statistics
    logger.info("\n" + "=" * 80)
    logger.info("✅ DATASET GENERATION COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"\n📊 Final Statistics:")
    logger.info(f"   Total trajectories: {len(all_data)}")
    logger.info(f"   Total steps: {total_clean + total_augmented}")
    logger.info(f"   Clean steps: {total_clean} ({total_clean/(total_clean+total_augmented)*100:.1f}%)")
    logger.info(f"   Augmented steps: {total_augmented} ({total_augmented/(total_clean+total_augmented)*100:.1f}%)")
    logger.info(f"\n📊 Failure Distribution:")
    for failure_type, count in total_failure_counts.most_common():
        percentage = (count / total_augmented) * 100 if total_augmented > 0 else 0
        logger.info(f"   {failure_type}: {count} ({percentage:.1f}%)")
    
    logger.info(f"\n📁 Output location: {output_dir.absolute()}")
    logger.info(f"   - augmented_trajectories.json")
    logger.info(f"   - summary.json")
    logger.info(f"   - images/ ({len(all_data)} task folders)")


if __name__ == "__main__":
    main()
