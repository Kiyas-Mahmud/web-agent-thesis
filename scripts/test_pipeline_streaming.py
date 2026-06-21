"""
Test pipeline with streaming mode - no massive download needed.

Usage:
    python scripts/test_pipeline_streaming.py --num-tasks 5
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.offline_data import MultimodalMind2WebLoader
from src.failure_injection import FailureEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Test pipeline with streaming mode")
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=5,
        help="Number of tasks to test (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/test_pilot",
        help="Output directory for generated data"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Testing Pipeline with Streaming Mode")
    logger.info("="*60)
    
    # Initialize loader in STREAMING mode (no download!)
    logger.info("\n📥 Initializing Mind2Web in streaming mode...")
    loader = MultimodalMind2WebLoader(use_streaming=True)
    
    success = loader.download_dataset()
    if not success:
        logger.error("❌ Failed to initialize streaming dataset")
        return 1
    
    logger.info("✅ Streaming mode initialized (no download required)")
    
    # Load sample trajectories
    logger.info(f"\n📊 Loading {args.num_tasks} trajectories...")
    trajectories = loader.load_trajectories(
        split="train",
        limit=args.num_tasks
    )
    
    if not trajectories:
        logger.error("❌ Failed to load trajectories")
        return 1
    
    logger.info(f"✅ Loaded {len(trajectories)} trajectories")
    
    # Print trajectory info
    total_steps = sum(len(t.steps) for t in trajectories)
    logger.info(f"   Total steps: {total_steps}")
    logger.info(f"   Avg steps per trajectory: {total_steps / len(trajectories):.1f}")
    
    # Initialize failure engine
    logger.info("\n🔧 Initializing failure injection engine...")
    engine = FailureEngine()
    
    # Test failure injection
    logger.info("\n🧪 Testing failure injection on sample trajectory...")
    test_traj = trajectories[0]
    logger.info(f"   Original trajectory: {test_traj.task_id}")
    logger.info(f"   Steps: {len(test_traj.steps)}")
    
    # Generate augmented version
    augmented = engine.inject_failure(test_traj)
    
    logger.info(f"\n✅ Generated augmented trajectory:")
    logger.info(f"   Failure type: {augmented.failure_type}")
    logger.info(f"   Failure step index: {augmented.failure_step_index}")
    logger.info(f"   Original steps: {len(test_traj.steps)}")
    logger.info(f"   Augmented steps: {len(augmented.steps)}")
    
    # Generate pilot dataset
    logger.info(f"\n🚀 Generating {args.num_tasks} augmented trajectories...")
    augmented_trajectories = []
    
    for idx, traj in enumerate(trajectories, 1):
        logger.info(f"   Processing {idx}/{len(trajectories)}: {traj.task_id}")
        aug_traj = engine.inject_failure(traj)
        augmented_trajectories.append(aug_traj)
        logger.info(f"      → {aug_traj.failure_type} failure injected at step {aug_traj.failure_step_index}")
    
    logger.info(f"\n✅ Generated {len(augmented_trajectories)} augmented trajectories")
    
    # Distribution analysis
    from collections import Counter
    failure_counts = Counter(t.failure_type for t in augmented_trajectories)
    
    logger.info("\n📊 Failure Type Distribution:")
    for failure_type, count in failure_counts.most_common():
        percentage = (count / len(augmented_trajectories)) * 100
        logger.info(f"   {failure_type}: {count} ({percentage:.1f}%)")
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n💾 Saving results to {output_dir}...")
    
    # Save augmented trajectories (simplified JSON)
    import json
    output_file = output_dir / "augmented_trajectories.json"
    
    with open(output_file, 'w') as f:
        data = []
        for traj in augmented_trajectories:
            data.append({
                'task_id': traj.task_id,
                'failure_type': traj.failure_type,
                'failure_step_index': traj.failure_step_index,
                'num_steps': len(traj.steps),
                'domain': traj.domain
            })
        json.dump(data, f, indent=2)
    
    logger.info(f"✅ Saved to {output_file}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Pipeline test completed successfully!")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
