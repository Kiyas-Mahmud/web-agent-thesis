"""
Test the offline augmentation pipeline with a small sample.

Usage:
    python scripts/test_offline_pipeline.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.offline_data import MultimodalMind2WebLoader
from src.failure_injection import (
    InjectionConfig,
    InjectionPipeline,
    TargetMissingInjector,
    MisclickInjector,
    WrongOperationInjector,
    NoStateChangeInjector,
    LoopInjector,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_loader():
    """Test the Mind2Web loader."""
    logger.info("="*60)
    logger.info("TEST 1: Mind2Web Loader")
    logger.info("="*60)
    
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline", use_streaming=True)
    
    # Load dataset in streaming mode
    logger.info("Loading dataset in streaming mode...")
    success = loader.download_dataset()
    
    if not success:
        logger.error("❌ Failed to load dataset")
        return False
    
    # Load test trajectories
    logger.info("\nLoading 5 test trajectories...")
    trajectories = loader.load_trajectories(limit=5)
    
    if not trajectories:
        logger.error("❌ No trajectories loaded. Dataset may not be accessible.")
        return False
    
    logger.info(f"✅ Loaded {len(trajectories)} trajectories")
    
    # Check first trajectory
    traj = trajectories[0]
    logger.info(f"\nSample trajectory:")
    logger.info(f"  Task ID: {traj.task_id}")
    logger.info(f"  Website: {traj.website}")
    logger.info(f"  Domain: {traj.domain}")
    logger.info(f"  Task: {traj.confirmed_task[:80]}...")
    logger.info(f"  Steps: {traj.num_steps}")
    
    # Check first step
    if traj.steps:
        step = traj.steps[0]
        logger.info(f"\nSample step:")
        logger.info(f"  Action: {step.action_type}")
        logger.info(f"  Target: {step.action_target[:60]}...")
        logger.info(f"  Has state_before: {step.state_before is not None}")
        logger.info(f"  Has state_after: {step.state_after is not None}")
        logger.info(f"  Has target_bbox: {step.target_bbox is not None}")
        logger.info(f"  Is valid: {step.is_valid}")
    
    return True


def test_injectors():
    """Test individual injectors."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Failure Injectors")
    logger.info("="*60)
    
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline", use_streaming=True)
    loader.download_dataset()
    trajectories = loader.load_trajectories(limit=1)
    
    if not trajectories:
        logger.error("❌ No trajectories for testing")
        return False
    
    traj = trajectories[0]
    config = InjectionConfig(random_seed=42)
    
    # Test each injector
    injectors = [
        ("TARGET_MISSING", TargetMissingInjector(config)),
        ("MISCLICK", MisclickInjector(config)),
        ("WRONG_OPERATION", WrongOperationInjector(config)),
        ("NO_STATE_CHANGE", NoStateChangeInjector(config)),
        ("LOOP", LoopInjector(config))
    ]
    
    for name, injector in injectors:
        # Find a step that can be injected
        injectable_steps = [s for s in traj.steps if injector.can_inject(s)]
        
        if injectable_steps:
            step = injectable_steps[0]
            logger.info(f"\n{name}:")
            logger.info(f"  Can inject: ✅ ({len(injectable_steps)}/{len(traj.steps)} steps)")
            
            # Try injection
            try:
                augmented = injector.inject(step, traj)
                logger.info(f"  Injection successful: ✅")
                logger.info(f"  Failure type: {augmented.failure_type}")
                logger.info(f"  Recovery strategy: {augmented.recovery_strategy}")
                logger.info(f"  Recovery success: {augmented.recovery_success}")
            except Exception as e:
                logger.error(f"  Injection failed: ❌ {e}")
        else:
            logger.info(f"\n{name}:")
            logger.info(f"  Can inject: ❌ (no suitable steps)")
    
    return True


def test_pipeline():
    """Test the full injection pipeline."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Injection Pipeline")
    logger.info("="*60)
    
    loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline", use_streaming=True)
    loader.download_dataset()
    trajectories = loader.load_trajectories(limit=3)
    
    if not trajectories:
        logger.error("❌ No trajectories for testing")
        return False
    
    # Initialize pipeline
    config = InjectionConfig(injection_rate=0.6, random_seed=42)
    pipeline = InjectionPipeline(config)
    
    # Register injectors
    pipeline.register_injector(TargetMissingInjector(config))
    pipeline.register_injector(MisclickInjector(config))
    pipeline.register_injector(WrongOperationInjector(config))
    pipeline.register_injector(NoStateChangeInjector(config))
    pipeline.register_injector(LoopInjector(config))
    
    logger.info(f"Pipeline configured with {len(pipeline.injectors)} injectors")
    logger.info(f"Injection rate: {config.injection_rate*100:.0f}%")
    
    # Process trajectories
    augmented_trajectories = []
    for traj in trajectories:
        augmented = pipeline.augment_trajectory(traj)
        augmented_trajectories.append(augmented)
    
    logger.info(f"\n✅ Processed {len(augmented_trajectories)} trajectories")
    
    # Show statistics
    stats = pipeline.get_statistics()
    logger.info(f"\nStatistics:")
    logger.info(f"  Total steps: {stats['total_steps_processed']}")
    logger.info(f"  Clean steps: {stats['clean_steps']}")
    logger.info(f"  Injected failures: {stats['injected_failures']}")
    
    if stats['injection_type_counts']:
        logger.info(f"\nInjection breakdown:")
        for injection_type, count in stats['injection_type_counts'].items():
            logger.info(f"  {injection_type}: {count}")
    
    # Show sample augmented step
    for traj in augmented_trajectories:
        injected_steps = [s for s in traj.augmented_steps if s.is_augmented]
        if injected_steps:
            step = injected_steps[0]
            logger.info(f"\nSample injected step:")
            logger.info(f"  Injection type: {step.injection_type}")
            logger.info(f"  Failure type: {step.failure_type}")
            logger.info(f"  Failure subtype: {step.failure_subtype}")
            logger.info(f"  Recovery strategy: {step.recovery_strategy}")
            logger.info(f"  Recovery success: {step.recovery_success}")
            break
    
    return True


def main():
    logger.info("Testing Offline Augmentation Pipeline")
    logger.info("="*60)
    
    try:
        # Test 1: Loader
        if not test_loader():
            logger.error("\n❌ Loader test failed. Is the dataset downloaded?")
            return 1
        
        # Test 2: Injectors
        if not test_injectors():
            logger.error("\n❌ Injector test failed")
            return 1
        
        # Test 3: Pipeline
        if not test_pipeline():
            logger.error("\n❌ Pipeline test failed")
            return 1
        
        logger.info("\n" + "="*60)
        logger.info("✅ All tests passed!")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
