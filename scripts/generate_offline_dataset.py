"""
Generate offline augmented dataset with failure injection.

Main script for generating the Phase 5 offline dataset:
1. Load Multimodal Mind2Web trajectories
2. Apply failure injection
3. Generate recovery steps
4. Save augmented dataset

Usage:
    python scripts/generate_offline_dataset.py --num-tasks 100 --output dataset/augmented_pilot
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List
import pickle

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.offline_data import MultimodalMind2WebLoader
from src.offline_data.offline_schema import AugmentedTrajectory
from src.offline_data.validate_dataset import DatasetValidator, check_dataset_balance
from src.failure_injection import (
    InjectionConfig,
    InjectionPipeline,
    TargetMissingInjector,
    MisclickInjector,
    WrongOperationInjector,
    NoStateChangeInjector,
    LoopInjector,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate offline augmented dataset")
    
    # Input/Output
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="dataset/mind2web_offline",
        help="Directory with cached Mind2Web dataset"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="dataset/augmented_pilot",
        help="Output directory for augmented dataset"
    )
    
    # Dataset selection
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "test_task", "test_website", "test_domain"],
        help="Dataset split to use"
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=100,
        help="Number of tasks to generate"
    )
    parser.add_argument(
        "--filter-domain",
        type=str,
        nargs="+",
        help="Filter by specific domains"
    )
    
    # Injection configuration
    parser.add_argument(
        "--injection-rate",
        type=float,
        default=0.6,
        help="Probability of injecting failure (0.0-1.0)"
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    # Validation
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated dataset"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip dataset download (use cached)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("="*60)
    logger.info("Offline Dataset Generation Pipeline")
    logger.info("="*60)
    logger.info(f"Output: {args.output_dir}")
    logger.info(f"Tasks: {args.num_tasks}")
    logger.info(f"Injection rate: {args.injection_rate*100:.0f}%")
    logger.info(f"Random seed: {args.random_seed}")
    
    # Step 1: Load Mind2Web dataset
    logger.info("\n" + "="*60)
    logger.info("STEP 1: Loading Multimodal Mind2Web Dataset")
    logger.info("="*60)
    
    # Use streaming mode by default to avoid large downloads
    loader = MultimodalMind2WebLoader(cache_dir=args.cache_dir, use_streaming=True)
    
    if not args.skip_download:
        logger.info("Connecting to HuggingFace dataset (streaming mode)...")
        success = loader.download_dataset()
        if not success:
            logger.error("❌ Dataset connection failed")
            return 1
    
    logger.info(f"Fetching {args.num_tasks} trajectories from {args.split} split...")
    logger.info("(This may take a few minutes on first run)")
    trajectories = loader.load_trajectories(
        split=args.split,
        limit=args.num_tasks,
        filter_by_domain=args.filter_domain
    )
    
    if not trajectories:
        logger.error("❌ No trajectories loaded")
        return 1
    
    logger.info(f"✅ Loaded {len(trajectories)} trajectories")
    
    # Validate original dataset
    if args.validate:
        logger.info("\nValidating original dataset...")
        validator = DatasetValidator()
        validation_report = validator.validate_trajectories(trajectories)
        logger.info(validator.get_quality_report())
    
    # Dataset balance
    balance_stats = check_dataset_balance(trajectories)
    logger.info(f"\nDataset balance:")
    logger.info(f"  Domains: {balance_stats['num_domains']}")
    logger.info(f"  Websites: {balance_stats['num_websites']}")
    logger.info(f"  Avg steps/trajectory: {balance_stats['avg_steps_per_trajectory']:.1f}")
    
    # Step 2: Initialize injection pipeline
    logger.info("\n" + "="*60)
    logger.info("STEP 2: Initializing Failure Injection Pipeline")
    logger.info("="*60)
    
    injection_config = InjectionConfig(
        injection_rate=args.injection_rate,
        random_seed=args.random_seed
    )
    
    pipeline = InjectionPipeline(injection_config)
    
    # Register all 5 injectors
    pipeline.register_injector(TargetMissingInjector(injection_config))
    pipeline.register_injector(MisclickInjector(injection_config))
    pipeline.register_injector(WrongOperationInjector(injection_config))
    pipeline.register_injector(NoStateChangeInjector(injection_config))
    pipeline.register_injector(LoopInjector(injection_config))
    
    logger.info(f"✅ Registered {len(pipeline.injectors)} injectors")
    
    # Step 3: Generate augmented dataset
    logger.info("\n" + "="*60)
    logger.info("STEP 3: Generating Augmented Dataset")
    logger.info("="*60)
    
    augmented_trajectories: List[AugmentedTrajectory] = []
    
    for idx, trajectory in enumerate(trajectories):
        if (idx + 1) % 10 == 0:
            logger.info(f"  Processing trajectory {idx+1}/{len(trajectories)}...")
        
        augmented_traj = pipeline.augment_trajectory(trajectory)
        augmented_trajectories.append(augmented_traj)
    
    logger.info(f"✅ Generated {len(augmented_trajectories)} augmented trajectories")
    
    # Step 4: Save augmented dataset
    logger.info("\n" + "="*60)
    logger.info("STEP 4: Saving Augmented Dataset")
    logger.info("="*60)
    
    # Save as pickle
    output_file = output_dir / "augmented_dataset.pkl"
    logger.info(f"Saving to {output_file}...")
    
    with open(output_file, 'wb') as f:
        pickle.dump(augmented_trajectories, f)
    
    logger.info(f"✅ Saved {len(augmented_trajectories)} trajectories to {output_file}")
    
    # Save metadata
    metadata = {
        "dataset_name": "offline_augmented_mind2web",
        "generated_at": datetime.now().isoformat(),
        "source_split": args.split,
        "num_trajectories": len(augmented_trajectories),
        "injection_config": {
            "injection_rate": injection_config.injection_rate,
            "random_seed": injection_config.random_seed,
            "target_distribution": injection_config.target_distribution,
            "failure_type_distribution": injection_config.failure_type_distribution,
            "recovery_success_rates": injection_config.recovery_success_rates
        }
    }
    
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✅ Saved metadata to {metadata_file}")
    
    # Step 5: Generate statistics
    logger.info("\n" + "="*60)
    logger.info("STEP 5: Dataset Statistics")
    logger.info("="*60)
    
    stats = pipeline.get_statistics()
    
    logger.info(f"\nPipeline Statistics:")
    logger.info(f"  Total steps processed: {stats['total_steps_processed']}")
    logger.info(f"  Clean steps: {stats['clean_steps']} ({stats['clean_steps']/stats['total_steps_processed']*100:.1f}%)")
    logger.info(f"  Injected failures: {stats['injected_failures']} ({stats['injected_failures']/stats['total_steps_processed']*100:.1f}%)")
    
    logger.info(f"\nInjection Type Distribution:")
    for injection_type, count in stats['injection_type_counts'].items():
        percentage = count / stats['injected_failures'] * 100 if stats['injected_failures'] > 0 else 0
        logger.info(f"  {injection_type}: {count} ({percentage:.1f}%)")
    
    # Count recovery statistics across all trajectories
    total_recoveries_attempted = sum(t.num_recoveries_attempted for t in augmented_trajectories)
    total_recoveries_successful = sum(t.num_recoveries_successful for t in augmented_trajectories)
    recovery_rate = (
        total_recoveries_successful / total_recoveries_attempted * 100 
        if total_recoveries_attempted > 0 else 0
    )
    
    logger.info(f"\nRecovery Statistics:")
    logger.info(f"  Recoveries attempted: {total_recoveries_attempted}")
    logger.info(f"  Recoveries successful: {total_recoveries_successful}")
    logger.info(f"  Recovery success rate: {recovery_rate:.1f}%")
    
    # Save statistics
    stats_file = output_dir / "statistics.json"
    stats["recovery_statistics"] = {
        "total_recoveries_attempted": total_recoveries_attempted,
        "total_recoveries_successful": total_recoveries_successful,
        "recovery_success_rate": recovery_rate
    }
    
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"\n✅ Saved statistics to {stats_file}")
    
    # Step 6: Validation
    if args.validate:
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Validating Augmented Dataset")
        logger.info("="*60)
        
        # Check distribution targets
        actual_clean_rate = stats['clean_steps'] / stats['total_steps_processed']
        actual_failure_rate = stats['injected_failures'] / stats['total_steps_processed']
        
        target_clean = injection_config.target_distribution['clean_success']
        target_failure = sum([
            injection_config.target_distribution['recoverable_failure'],
            injection_config.target_distribution['non_recoverable'],
            injection_config.target_distribution['ambiguous']
        ])
        
        logger.info(f"\nDistribution Check:")
        logger.info(f"  Target clean rate: {target_clean*100:.0f}%")
        logger.info(f"  Actual clean rate: {actual_clean_rate*100:.1f}%")
        logger.info(f"  Deviation: {abs(actual_clean_rate - target_clean)*100:.1f}%")
        
        logger.info(f"\n  Target failure rate: {target_failure*100:.0f}%")
        logger.info(f"  Actual failure rate: {actual_failure_rate*100:.1f}%")
        logger.info(f"  Deviation: {abs(actual_failure_rate - target_failure)*100:.1f}%")
        
        # Check recovery rate target (55-65%)
        target_recovery_min = 55
        target_recovery_max = 65
        
        if target_recovery_min <= recovery_rate <= target_recovery_max:
            logger.info(f"\n✅ Recovery rate {recovery_rate:.1f}% within target range ({target_recovery_min}-{target_recovery_max}%)")
        else:
            logger.warning(f"\n⚠️  Recovery rate {recovery_rate:.1f}% outside target range ({target_recovery_min}-{target_recovery_max}%)")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Dataset Generation Complete!")
    logger.info("="*60)
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"  - augmented_dataset.pkl ({len(augmented_trajectories)} trajectories)")
    logger.info(f"  - metadata.json")
    logger.info(f"  - statistics.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
