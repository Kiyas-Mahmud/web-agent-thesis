"""
Quick diagnostic - check cached Mind2Web data structure
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("MIND2WEB DATA DIAGNOSTIC")
print("="*80)

# Load the loader
from src.offline_data import MultimodalMind2WebLoader

print("\nLoading Mind2Web from cache...")
loader = MultimodalMind2WebLoader(
    cache_dir="dataset/mind2web_offline",
    use_streaming=False
)

# Try to load from cache without triggering downloads
try:
    loader.load_from_cache()
    print("✅ Dataset loaded from cache")
except Exception as e:
    print(f"❌ Failed to load: {e}")
    exit(1)

# Load trajectories WITHOUT screenshots first (fast)
print("\nLoading trajectories (without screenshots)...")
trajectories = loader.load_trajectories(
    split='train',
    limit=None,
    load_screenshots=False
)

print(f"\n📊 RESULTS:")
print(f"   Total trajectories: {len(trajectories)}")

if trajectories:
    # Check first trajectory
    first = trajectories[0]
    print(f"\n   First trajectory:")
    print(f"   - Task ID: {first.task_id}")
    print(f"   - Steps: {len(first.steps)}")
    print(f"   - Website: {first.website if hasattr(first, 'website') else 'N/A'}")
    
    if first.steps:
        step = first.steps[0]
        print(f"\n   First step structure:")
        print(f"   - action_type: {step.action_type}")
        print(f"   - action_target: {step.action_target}")
        print(f"   - has state_before: {hasattr(step, 'state_before')}")
        print(f"   - has state_after: {hasattr(step, 'state_after')}")
        
        if hasattr(step, 'state_before') and step.state_before:
            print(f"   - state_before type: {type(step.state_before)}")
            print(f"   - state_before has screenshot attr: {hasattr(step.state_before, 'screenshot')}")

# Count total steps
total_steps = sum(len(t.steps) for t in trajectories)
avg_steps = total_steps / len(trajectories) if trajectories else 0

print(f"\n📈 STATISTICS:")
print(f"   Total steps: {total_steps}")
print(f"   Avg steps/trajectory: {avg_steps:.1f}")
print(f"   Can reach 10K? {'YES ✅' if total_steps >= 10000 else f'NO ❌ (only {total_steps} available)'}")

# Now try loading ONE trajectory WITH screenshots
print(f"\n🖼️  SCREENSHOT TEST:")
print("   Loading 1 trajectory with screenshots...")
try:
    test_trajs = loader.load_trajectories(
        split='train',
        limit=1,
        load_screenshots=True
    )
    
    if test_trajs and test_trajs[0].steps:
        test_step = test_trajs[0].steps[0]
        if hasattr(test_step.state_before, 'screenshot') and test_step.state_before.screenshot:
            img = test_step.state_before.screenshot
            print(f"   ✅ Screenshot loaded successfully")
            print(f"   - Type: {type(img)}")
            print(f"   - Size: {img.size if hasattr(img, 'size') else 'unknown'}")
        else:
            print(f"   ❌ No screenshot found in step.state_before")
    else:
        print(f"   ❌ No trajectories or steps found")
except Exception as e:
    print(f"   ❌ Failed to load screenshots: {e}")

print("\n" + "="*80)
print("RECOMMENDATION:")
if total_steps >= 10000:
    print("✅ You have enough data (23 cached files)")
    print("   Proceed with generation")
else:
    print(f"⚠️  Only {total_steps} steps available")
    print("   Options:")
    print("   1. Download remaining 4 files (get to 10K+)")
    print("   2. Generate with what you have (~{} steps)".format(total_steps))
print("="*80)
