"""
Quick test to verify the batch script components work correctly
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.offline_data import MultimodalMind2WebLoader

print("="*70)
print("TESTING BATCH SCRIPT COMPONENTS")
print("="*70)

# Test 1: Load dataset
print("\n[TEST 1] Loading dataset...")
try:
    loader = MultimodalMind2WebLoader(
        cache_dir="dataset/mind2web_offline",
        use_streaming=False
    )
    loader.load_from_cache()
    print("✅ Dataset loaded successfully")
except Exception as e:
    print(f"❌ Failed to load dataset: {e}")
    sys.exit(1)

# Test 2: Load metadata only (no screenshots)
print("\n[TEST 2] Loading trajectory IDs (metadata only)...")
try:
    trajs = loader.load_trajectories(
        split='train',
        limit=10,
        load_screenshots=False
    )
    print(f"✅ Loaded {len(trajs)} trajectories")
    if trajs:
        print(f"   First trajectory ID: {trajs[0].task_id}")
        print(f"   Steps: {len(trajs[0].steps)}")
except Exception as e:
    print(f"❌ Failed to load trajectories: {e}")
    sys.exit(1)

# Test 3: Filter by specific IDs
print("\n[TEST 3] Testing filter_by_ids parameter...")
try:
    # Get first 3 IDs
    test_ids = [t.task_id for t in trajs[:3]]
    print(f"   Target IDs: {test_ids}")
    
    # Load with filter
    filtered = loader.load_trajectories(
        split='train',
        filter_by_ids=test_ids,
        load_screenshots=False
    )
    print(f"✅ Loaded {len(filtered)} trajectories with filter")
    
    # Verify all returned IDs are in test_ids
    returned_ids = [t.task_id for t in filtered]
    all_match = all(rid in test_ids for rid in returned_ids)
    
    if all_match:
        print(f"✅ All returned IDs match filter")
    else:
        print(f"❌ Some IDs don't match filter!")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Failed to filter trajectories: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Load with screenshots (small batch)
print("\n[TEST 4] Loading 2 trajectories WITH screenshots...")
try:
    small_batch = loader.load_trajectories(
        split='train',
        limit=2,
        load_screenshots=True
    )
    print(f"✅ Loaded {len(small_batch)} trajectories with screenshots")
    
    # Check if screenshots exist
    if small_batch and small_batch[0].steps:
        first_step = small_batch[0].steps[0]
        has_before = first_step.state_before is not None
        has_after = first_step.state_after is not None
        print(f"   state_before exists: {has_before}")
        print(f"   state_after exists: {has_after}")
        
        if has_before:
            print(f"   state_before size: {first_step.state_before.size}")
            
except Exception as e:
    print(f"❌ Failed to load with screenshots: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70)
print("\nThe batch script should work correctly.")
print("Run: python generate_10k_batch_fixed.py")
