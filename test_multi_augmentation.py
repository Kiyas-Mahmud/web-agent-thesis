"""
Test multi-augmentation logic on 10 trajectories before full generation
"""
import logging
from pathlib import Path
from collections import Counter

from src.offline_data.mind2web_loader import MultimodalMind2WebLoader
from src.offline_augmentation.injectors.wrong_operation_injector import WrongOperationInjector
from src.offline_augmentation.injectors.no_state_change_injector import NoStateChangeInjector
from src.offline_augmentation.injectors.target_missing_injector import TargetMissingInjector
from src.offline_augmentation.injectors.misclick_injector import MisclickInjector
from src.offline_augmentation.injectors.loop_injector import LOOPInjector
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)

def apply_multi_augmentation(clean_step, injectors, num_augmentations=4):
    """Apply multiple different augmentations to a single clean step"""
    augmented_versions = []
    
    # Shuffle injectors for random selection
    available_injectors = injectors.copy()
    random.shuffle(available_injectors)    
    # Apply up to num_augmentations different injectors
    for injector in available_injectors[:num_augmentations]:
        try:
            augmented = injector.inject(clean_step)
            if augmented and augmented.is_augmented:
                augmented_versions.append(augmented)
        except Exception as e:
            logger.debug(f"Failed to apply {injector.__class__.__name__}: {e}")
            continue
    
    return augmented_versions

# Initialize
loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
loader.load_from_cache()

injectors = [
    TargetMissingInjector(),
    MisclickInjector(),
    WrongOperationInjector(),
    NoStateChangeInjector(),
    LOOPInjector()
]

print("="*70)
print("TESTING MULTI-AUGMENTATION ON 10 TRAJECTORIES")
print("="*70)

# Load 10 trajectories from train
trajs = loader.load_trajectories(split='train', limit=10, load_screenshots=True)
print(f"\nLoaded {len(trajs)} trajectories")

clean_count = 0
augmented_count = 0
failure_counts = Counter()

for traj in trajs:
    for step in traj.steps:
        clean_count += 1
        
        # Apply multi-augmentation
        augmented_versions = apply_multi_augmentation(step, injectors, num_augmentations=4)
        augmented_count += len(augmented_versions)
        
        for aug in augmented_versions:
            failure_counts[aug.injection_type] += 1

print(f"\n📊 RESULTS:")
print(f"   Clean steps: {clean_count}")
print(f"   Augmented steps: {augmented_count}")
print(f"   Total steps: {clean_count + augmented_count}")
print(f"   Augmentation ratio: {augmented_count / clean_count:.2f}x")
print(f"\n   Failure distribution:")
for failure_type, count in failure_counts.most_common():
    percentage = count / augmented_count * 100
    print(f"     {failure_type}: {count} ({percentage:.1f}%)")

expected_total = clean_count * 5  # 1 clean + 4 augmented per step
print(f"\n✅ Expected total with perfect augmentation: {expected_total}")
print(f"   Actual total: {clean_count + augmented_count}")
print(f"   Coverage: {(clean_count + augmented_count) / expected_total * 100:.1f}%")

if augmented_count >= clean_count * 3:
    print(f"\n✅ Multi-augmentation working! Getting {augmented_count / clean_count:.1f} augmentations per step")
    print("   Ready for full 70k generation")
else:
    print(f"\n⚠️  Low augmentation rate. Expected ~4x, got {augmented_count / clean_count:.1f}x")
    print("   May need to adjust injector logic or check data compatibility")

print("="*70)
