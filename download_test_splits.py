"""
Download and analyze test splits from Mind2Web to determine data structure and quantity
"""
from src.offline_data.mind2web_loader import MultimodalMind2WebLoader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("="*70)
print("DOWNLOADING TEST SPLITS FROM MIND2WEB")
print("="*70)

# Initialize loader (will download full dataset with all splits)
loader = MultimodalMind2WebLoader(
    cache_dir="dataset/mind2web_offline",
    use_streaming=False  # Download full dataset
)

# Download dataset (this will get all splits)
logger.info("\n📥 Downloading full Mind2Web dataset...")
logger.info("This includes: train, test_domain, test_task, test_website")
logger.info("Note: This may take 10-30 minutes depending on connection speed\n")

success = loader.download_dataset(force_download=False, max_retries=3)

if success:
    print("\n✅ Download successful!")
    print("\nNow analyzing data structure...")
    
    # Analyze each split
    splits = ['train', 'test_domain', 'test_task', 'test_website']
    total_trajectories = 0
    total_steps = 0
    
    print("\n" + "="*70)
    print("DETAILED ANALYSIS BY SPLIT:")
    print("="*70)
    
    for split in splits:
        try:
            print(f"\n📊 {split.upper()}:")
            
            # Load trajectories without screenshots (metadata only for speed)
            trajs = loader.load_trajectories(
                split=split,
                limit=None,
                load_screenshots=False
            )
            
            num_trajs = len(trajs)
            num_steps = sum(len(t.steps) for t in trajs)
            
            total_trajectories += num_trajs
            total_steps += num_steps
            
            print(f"   Trajectories: {num_trajs:,}")
            print(f"   Steps: {num_steps:,}")
            print(f"   Avg steps/trajectory: {num_steps/num_trajs:.1f}")
            
        except Exception as e:
            print(f"   Error loading {split}: {e}")
    
    print("\n" + "="*70)
    print("TOTAL AVAILABLE DATA:")
    print("="*70)
    print(f"   Total Trajectories: {total_trajectories:,}")
    print(f"   Total Clean Steps: {total_steps:,}")
    print(f"\n   With 60% augmentation: {int(total_steps * 1.6):,} steps")
    print(f"   With 100% augmentation: {int(total_steps * 2):,} steps")
    print(f"   With 200% augmentation: {int(total_steps * 3):,} steps")
    print(f"   With 400% augmentation: {int(total_steps * 5):,} steps")
    
    print("\n" + "="*70)
    print("PATH TO 70K+ DATASET:")
    print("="*70)
    
    if total_steps * 1.6 >= 70000:
        print(f"✅ Can reach 70k with 60% augmentation")
    elif total_steps * 2 >= 70000:
        print(f"⚠️  Need 100% augmentation to reach 70k")
        print(f"   Current: 60% → {int(total_steps * 1.6):,}")
        print(f"   Needed: 100% → {int(total_steps * 2):,}")
    elif total_steps * 3 >= 70000:
        print(f"⚠️  Need 200% augmentation to reach 70k")
        print(f"   Strategy: Apply 2 augmentations per step")
    elif total_steps * 5 >= 70000:
        print(f"⚠️  Need 400% augmentation to reach 70k")
        print(f"   Strategy: Apply 4 augmentations per step")
    else:
        print(f"❌ Cannot reach 70k with available Mind2Web data alone")
        print(f"   Max possible: {int(total_steps * 5):,} steps (with 4x augmentation)")
        print(f"   Need additional data sources")
    
    print("="*70)
    
else:
    print("\n❌ Download failed. Check logs above for details.")
