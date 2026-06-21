"""Check available Mind2Web data across all splits"""
from src.offline_data.mind2web_loader import MultimodalMind2WebLoader

print("="*70)
print("CHECKING AVAILABLE MIND2WEB DATA")
print("="*70)

loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
loader.load_from_cache()

splits = ['train', 'test_domain', 'test_task', 'test_website']

print("\n📊 DATA AVAILABILITY BY SPLIT:")
total_trajectories = 0
total_steps = 0

for split in splits:
    try:
        print(f"\n  {split.upper()}:")
        trajs = loader.load_trajectories(split=split, limit=None, load_screenshots=False)
        num_trajs = len(trajs)
        num_steps = sum(len(t.steps) for t in trajs)
        total_trajectories += num_trajs
        total_steps += num_steps
        print(f"    Trajectories: {num_trajs}")
        print(f"    Steps: {num_steps}")
        print(f"    Avg steps/trajectory: {num_steps/num_trajs:.1f}")
    except Exception as e:
        print(f"    Error: {e}")

print(f"\n{'='*70}")
print(f"TOTAL AVAILABLE:")
print(f"  Trajectories: {total_trajectories}")
print(f"  Steps: {total_steps}")
print(f"\nCURRENTLY USED (train only):")
print(f"  Trajectories: 1,009 (100% of train)")
print(f"  Steps: 7,775")
print(f"\nAVAILABLE TO ADD:")
print(f"  Test splits: {total_steps - 7775} additional steps")
print(f"\nPOTENTIAL WITH TEST DATA:")
print(f"  Total steps if we use ALL data: {total_steps}")
print(f"  With 60% augmentation: ~{int(total_steps * 1.6)} steps")
print(f"  With 100% augmentation: ~{total_steps * 2} steps")
print("="*70)
