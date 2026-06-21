"""Quick test to verify all splits are accessible"""
from src.offline_data.mind2web_loader import MultimodalMind2WebLoader

print("="*70)
print("TESTING ALL SPLITS ACCESSIBILITY")
print("="*70)

loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline", use_streaming=False)

print("\nLoading dataset (will use cache)...")
success = loader.download_dataset()

if not success:
    print("❌ Failed to load dataset!")
    exit(1)

print(f"\n✅ Dataset loaded")
print(f"Available splits: {list(loader.dataset.keys())}")

# Test each split
splits_to_test = ['train', 'test_domain', 'test_task', 'test_website']
total_trajs = 0
total_steps = 0

print(f"\n{'='*70}")
print("TESTING EACH SPLIT:")
print(f"{'='*70}")

for split in splits_to_test:
    try:
        print(f"\n{split.upper()}:")
        if split not in loader.dataset:
            print(f"  ❌ Not found in dataset.keys()")
            continue
            
        trajs = loader.load_trajectories(split=split, limit=None, load_screenshots=False)
        num_trajs = len(trajs)
        num_steps = sum(len(t.steps) for t in trajs)
        total_trajs += num_trajs
        total_steps += num_steps
        
        print(f"  ✅ Trajectories: {num_trajs}")
        print(f"  ✅ Steps: {num_steps}")
        print(f"  ✅ Avg steps/traj: {num_steps/num_trajs:.1f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print(f"\n{'='*70}")
print(f"SUMMARY:")
print(f"  Total trajectories: {total_trajs}")
print(f"  Total steps: {total_steps}")
print(f"  With 60% augmentation: ~{int(total_steps * 1.6)} steps")
print(f"  With 100% augmentation: ~{total_steps * 2} steps")
print(f"{'='*70}")

if total_steps >= 10000:
    print(f"\n✅ EXCELLENT! With {total_steps} clean steps, you can easily reach 15K+")
else:
    print(f"\n⚠️ Only {total_steps} steps available. May need higher augmentation rate.")
