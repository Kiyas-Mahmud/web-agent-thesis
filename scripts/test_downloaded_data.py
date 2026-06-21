"""
Test pipeline with downloaded data (no streaming, use cached files).

Usage:
    python scripts/test_downloaded_data.py --num-tasks 10
"""

import argparse
import logging
import sys
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(description="Test pipeline with downloaded data")
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=10,
        help="Number of tasks to generate (default: 10)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/pilot_test",
        help="Output directory for generated data"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Testing Pipeline with Downloaded Data")
    logger.info("="*60)
    
    # Initialize loader with cache (not streaming)
    logger.info("\n📥 Loading Mind2Web from cached parquet files...")
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False  # Use downloaded files
    )
    
    # Load from cache (doesn't trigger new downloads)
    success = loader.load_from_cache()
    if not success:
        logger.error("❌ Failed to load dataset from cache")
        return 1
    
    logger.info("✅ Dataset loaded from cache")
    
    # Get dataset info
    logger.info("\n📊 Dataset Information:")
    info = loader.get_dataset_info()
    if info:
        for key, value in info.items():
            if key == "splits":
                logger.info(f"\n  Splits:")
                for split_name, split_info in value.items():
                    logger.info(f"    {split_name}: {split_info['num_samples']} samples")
            else:
                logger.info(f"  {key}: {value}")
    
    # Load sample trajectories
    logger.info(f"\n📊 Loading {args.num_tasks} trajectories from train split...")
    trajectories = loader.load_trajectories(
        split="train",
        limit=args.num_tasks,
        load_screenshots=True  # Enable screenshot loading for failure injection
    )
    
    if not trajectories:
        logger.error("❌ Failed to load trajectories")
        return 1
    
    logger.info(f"✅ Loaded {len(trajectories)} trajectories")
    
    # Print trajectory info
    total_steps = sum(len(t.steps) for t in trajectories)
    logger.info(f"   Total steps: {total_steps}")
    logger.info(f"   Avg steps per trajectory: {total_steps / len(trajectories):.1f}")
    
    # Show sample trajectory details
    logger.info(f"\n🔍 Sample Trajectory Details:")
    sample_traj = trajectories[0]
    logger.info(f"   Task ID: {sample_traj.task_id}")
    logger.info(f"   Domain: {sample_traj.domain}")
    logger.info(f"   Website: {sample_traj.website}")
    logger.info(f"   Steps: {len(sample_traj.steps)}")
    logger.info(f"   First step action: {sample_traj.steps[0].action_type if sample_traj.steps else 'N/A'}")
    
    # Check if screenshots were loaded
    screenshots_loaded = sum(1 for t in trajectories for s in t.steps if s.state_before is not None)
    logger.info(f"   Screenshots loaded: {screenshots_loaded}/{total_steps}")
    if screenshots_loaded == 0:
        logger.warning("⚠️  No screenshots loaded! Failure injection may not work.")
    
    # Initialize failure engine
    logger.info("\n🔧 Initializing failure injection pipeline...")
    config = InjectionConfig(injection_rate=0.6)
    pipeline = InjectionPipeline(config)
    
    # Register all injectors
    pipeline.register_injector(TargetMissingInjector(config))
    pipeline.register_injector(MisclickInjector(config))
    pipeline.register_injector(WrongOperationInjector(config))
    pipeline.register_injector(NoStateChangeInjector(config))
    pipeline.register_injector(LoopInjector(config))
    
    logger.info("✅ Registered 5 failure injectors")
    
    # Generate augmented trajectories
    logger.info(f"\n🚀 Generating {args.num_tasks} augmented trajectories...")
    augmented_trajectories = []
    
    for idx, traj in enumerate(trajectories, 1):
        logger.info(f"   [{idx}/{len(trajectories)}] Processing: {traj.task_id}")
        try:
            aug_traj = pipeline.augment_trajectory(traj)
            augmented_trajectories.append(aug_traj)
            
            # Count injected failures in this trajectory
            injected = sum(1 for step in aug_traj.augmented_steps if step.is_augmented)
            logger.info(f"      → {injected}/{len(aug_traj.augmented_steps)} steps with failures injected")
        except Exception as e:
            logger.warning(f"      ⚠️  Failed to inject: {e}")
    
    logger.info(f"\n✅ Generated {len(augmented_trajectories)} augmented trajectories")
    
    # Distribution analysis
    from collections import Counter
    
    # Count failure types across all augmented steps
    failure_type_counts = Counter()
    total_augmented_steps = 0
    total_clean_steps = 0
    
    for traj in augmented_trajectories:
        for step in traj.augmented_steps:
            if step.is_augmented:
                total_augmented_steps += 1
                if hasattr(step, 'injection_type'):
                    failure_type_counts[step.injection_type] += 1
            else:
                total_clean_steps += 1
    
    logger.info("\n📊 Injection Statistics:")
    logger.info(f"   Total steps: {total_augmented_steps + total_clean_steps}")
    logger.info(f"   Clean steps: {total_clean_steps} ({total_clean_steps/(total_augmented_steps + total_clean_steps)*100:.1f}%)")
    logger.info(f"   Augmented steps: {total_augmented_steps} ({total_augmented_steps/(total_augmented_steps + total_clean_steps)*100:.1f}%)")
    
    logger.info("\n📊 Failure Type Distribution:")
    for failure_type, count in failure_type_counts.most_common():
        percentage = (count / total_augmented_steps) * 100 if total_augmented_steps > 0 else 0
        logger.info(f"   {failure_type}: {count} ({percentage:.1f}%)")
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n💾 Saving results to {output_dir}...")
    
    # Save augmented trajectories (full JSON with step details)
    import json
    from PIL import Image
    import numpy as np
    
    # Create images directory
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "augmented_trajectories.json"
    
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
            data['action_type'] = step.original_step.action_type
            data['step_number'] = step.original_step.step_number
            data['task_id'] = step.original_step.task_id
            data['action_target'] = step.original_step.action_target
            data['action_coords'] = step.original_step.action_coords
            
            # Save screenshots and add paths
            orig_step = step.original_step
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
    
    logger.info(f"💾 Exporting screenshots to {images_dir}...")
    
    with open(output_file, 'w') as f:
        data = []
        for traj_idx, traj in enumerate(augmented_trajectories):
            orig_traj = traj.original_trajectory
            
            # Create task-specific images directory
            task_images_dir = images_dir / f"task_{traj_idx:04d}"
            task_images_dir.mkdir(exist_ok=True)
            
            data.append({
                'task_id': orig_traj.task_id,
                'domain': orig_traj.domain,
                'website': orig_traj.website,
                'confirmed_task': orig_traj.confirmed_task if hasattr(orig_traj, 'confirmed_task') else '',
                'num_steps': len(traj.augmented_steps),
                'num_augmented': sum(1 for s in traj.augmented_steps if s.is_augmented),
                'num_clean': sum(1 for s in traj.augmented_steps if not s.is_augmented),
                'steps': [serialize_step(s, task_images_dir, step_idx) for step_idx, s in enumerate(traj.augmented_steps)]
            })
            
            # Progress logging
            if (traj_idx + 1) % 10 == 0:
                logger.info(f"   Exported {traj_idx + 1}/{len(augmented_trajectories)} trajectories...")
        
        json.dump(data, f, indent=2)
    
    logger.info(f"✅ Saved to {output_file}")
    logger.info(f"✅ Screenshots exported to {images_dir}")
    
    # Save summary
    summary_file = output_dir / "summary.json"
    summary = {
        'total_trajectories': len(augmented_trajectories),
        'total_steps': total_augmented_steps + total_clean_steps,
        'clean_steps': total_clean_steps,
        'augmented_steps': total_augmented_steps,
        'avg_steps_per_trajectory': (total_augmented_steps + total_clean_steps) / len(augmented_trajectories) if augmented_trajectories else 0,
        'failure_distribution': dict(failure_type_counts),
        'pipeline_statistics': pipeline.get_statistics()
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"✅ Summary saved to {summary_file}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Pipeline test completed successfully!")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
