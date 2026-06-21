"""
Analyze dataset and update the markdown report with actual statistics
"""
import json
from pathlib import Path
from collections import Counter

print("Analyzing dataset...")

# Load dataset
dataset_path = Path("output/dataset_10k_final")
with open(dataset_path / "augmented_trajectories.json", 'r') as f:
    data = json.load(f)

with open(dataset_path / "summary.json", 'r') as f:
    summary = json.load(f)

# Collect statistics
total_trajectories = len(data)
total_steps = sum(len(t['steps']) for t in data)
clean_steps = summary['clean_steps']
augmented_steps = summary['augmented_steps']

# Analyze labels
action_types = Counter()
failure_types = summary['failure_counts']
has_coords = 0
has_before_image = 0
has_after_image = 0
has_both_images = 0

for traj in data:
    for step in traj['steps']:
        # Action types
        if step.get('action_type'):
            action_types[step['action_type']] += 1
        
        # Coordinates
        if step.get('action_coords'):
            has_coords += 1
        
        # Images
        if step.get('state_before_image'):
            has_before_image += 1
        if step.get('state_after_image'):
            has_after_image += 1
        if step.get('state_before_image') and step.get('state_after_image'):
            has_both_images += 1

# Count images
images_dir = dataset_path / "images"
total_image_files = len(list(images_dir.glob("**/*.jpg")))
task_folders = len(list(images_dir.glob("task_*")))

# Print detailed report
print("\n" + "="*80)
print("DATASET ANALYSIS - DETAILED STATISTICS")
print("="*80)

print(f"\n📊 OVERVIEW:")
print(f"  Total Trajectories: {total_trajectories:,}")
print(f"  Total Steps: {total_steps:,}")
print(f"  Clean Steps: {clean_steps:,} ({clean_steps/total_steps*100:.1f}%)")
print(f"  Augmented Steps: {augmented_steps:,} ({augmented_steps/total_steps*100:.1f}%)")

print(f"\n🏷️  ACTION TYPE LABELS ({len(action_types)} types):")
for action_type, count in action_types.most_common():
    percentage = count / total_steps * 100
    bar = "█" * int(percentage / 2) + "░" * (50 - int(percentage / 2))
    print(f"  {action_type:<20} {count:>6,} ({percentage:>5.1f}%) {bar[:30]}")

print(f"\n🔥 FAILURE TYPE LABELS ({len(failure_types)} types):")
for failure_type, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
    percentage = count / augmented_steps * 100 if augmented_steps > 0 else 0
    bar = "█" * int(percentage / 2) + "░" * (50 - int(percentage / 2))
    print(f"  {failure_type:<20} {count:>6,} ({percentage:>5.1f}%) {bar[:30]}")

print(f"\n📍 COORDINATES:")
print(f"  Steps with coordinates: {has_coords:,} ({has_coords/total_steps*100:.1f}%)")
print(f"  Steps without coordinates: {total_steps-has_coords:,} ({(total_steps-has_coords)/total_steps*100:.1f}%)")

print(f"\n🖼️  IMAGES:")
print(f"  Total image files: {total_image_files:,}")
print(f"  Task folders: {task_folders:,}")
print(f"  Expected images: {total_steps * 2:,}")
print(f"  Missing: {total_steps * 2 - total_image_files:,} ({(total_steps*2-total_image_files)/(total_steps*2)*100:.1f}%)")
print(f"  Success rate: {total_image_files/(total_steps*2)*100:.1f}%")
print(f"\n  Steps with BEFORE image: {has_before_image:,} ({has_before_image/total_steps*100:.1f}%)")
print(f"  Steps with AFTER image: {has_after_image:,} ({has_after_image/total_steps*100:.1f}%)")
print(f"  Steps with BOTH images: {has_both_images:,} ({has_both_images/total_steps*100:.1f}%)")

print("\n" + "="*80)
print("✅ Analysis complete! Report saved at:")
print(f"   {dataset_path / 'DATASET_REPORT.md'}")
print("="*80)

# Create summary stats file
stats = {
    "overview": {
        "total_trajectories": total_trajectories,
        "total_steps": total_steps,
        "clean_steps": clean_steps,
        "augmented_steps": augmented_steps,
        "augmentation_rate": f"{augmented_steps/total_steps*100:.1f}%"
    },
    "action_types": dict(action_types.most_common()),
    "failure_types": failure_types,
    "coordinates": {
        "with_coords": has_coords,
        "without_coords": total_steps - has_coords,
        "percentage": f"{has_coords/total_steps*100:.1f}%"
    },
    "images": {
        "total_files": total_image_files,
        "task_folders": task_folders,
        "expected": total_steps * 2,
        "missing": total_steps * 2 - total_image_files,
        "success_rate": f"{total_image_files/(total_steps*2)*100:.1f}%",
        "steps_with_both": has_both_images
    }
}

with open(dataset_path / "detailed_statistics.json", 'w') as f:
    json.dump(stats, f, indent=2)

print(f"\n💾 Detailed statistics saved to: {dataset_path / 'detailed_statistics.json'}")
