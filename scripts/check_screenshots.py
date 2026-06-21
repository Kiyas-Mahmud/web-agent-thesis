"""Quick script to check if screenshots are loaded."""
import sys
sys.path.insert(0, "e:/University/thesis/datacollection")

from src.offline_data import MultimodalMind2WebLoader

loader = MultimodalMind2WebLoader(use_streaming=False)
print("Loading from cache...")
loader.load_from_cache()

print("Loading 2 trajectories with screenshots...")
trajectories = loader.load_trajectories(split="train", limit=2, load_screenshots=True)

print(f"Loaded {len(trajectories)} trajectories")
for i, traj in enumerate(trajectories):
    print(f"\nTrajectory {i+1}: {traj.task_id}")
    print(f"  Steps: {len(traj.steps)}")
    screenshots_count = sum(1 for s in traj.steps if s.state_before is not None)
    print(f"  Screenshots loaded: {screenshots_count}/{len(traj.steps)}")
    
    # Check first step details
    if traj.steps:
        step = traj.steps[0]
        print(f"  First step:")
        print(f"    - action_type: {step.action_type}")
        print(f"    - has state_before: {step.state_before is not None}")
        print(f"    - has target_bbox: {step.target_bbox is not None}")
        print(f"    - is_valid: {step.is_valid}")
