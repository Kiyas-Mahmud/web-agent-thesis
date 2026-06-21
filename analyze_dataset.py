"""Quick analysis of generated dataset"""
import json
from pathlib import Path

# Load dataset
print("="*70)
print("DATASET ANALYSIS")
print("="*70)

with open('output/dataset_10k_final/augmented_trajectories.json', 'r') as f:
    data = json.load(f)

print(f"\n📊 OVERALL STATISTICS:")
print(f"   Total Trajectories: {len(data)}")

total_steps = sum(len(t['steps']) for t in data)
print(f"   Total Steps (Rows): {total_steps}")

# Count by augmentation status
augmented_count = 0
clean_count = 0
failure_types = {}

for traj in data:
    for step in traj['steps']:
        if step['is_augmented']:
            augmented_count += 1
            ft = step['injection_type']
            if ft:
                failure_types[ft] = failure_types.get(ft, 0) + 1
        else:
            clean_count += 1

print(f"\n📈 ROW BREAKDOWN:")
print(f"   Clean Rows: {clean_count} ({clean_count/total_steps*100:.1f}%)")
print(f"   Augmented Rows: {augmented_count} ({augmented_count/total_steps*100:.1f}%)")

print(f"\n🔥 FAILURE TYPE DISTRIBUTION:")
for ft, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
    pct = count / augmented_count * 100 if augmented_count > 0 else 0
    print(f"   {ft}: {count} ({pct:.1f}%)")

# Check for nulls
print(f"\n🔍 DATA QUALITY:")
null_action_types = sum(1 for t in data for s in t['steps'] if not s['action_type'])
null_targets = sum(1 for t in data for s in t['steps'] if not s['action_target'])
null_task_ids = sum(1 for t in data for s in t['steps'] if not s['task_id'])

print(f"   Null action_type: {null_action_types}")
print(f"   Null action_target: {null_targets}")
print(f"   Null task_id: {null_task_ids}")

# Check duplicates
from collections import Counter
task_ids = [t['task_id'] for t in data]
duplicates = {k: v for k, v in Counter(task_ids).items() if v > 1}

print(f"\n🔄 DUPLICATE CHECK:")
print(f"   Unique trajectories: {len(set(task_ids))}")
print(f"   Duplicate trajectory IDs: {len(duplicates)}")

# Image statistics
images_dir = Path("output/dataset_10k_final/images")
total_images = len(list(images_dir.glob("**/*.jpg")))
expected_images = total_steps * 2
missing_images = expected_images - total_images

print(f"\n🖼️  IMAGE STATISTICS:")
print(f"   Images saved: {total_images}")
print(f"   Expected: {expected_images} (2 per step)")
print(f"   Missing: {missing_images} ({missing_images/expected_images*100:.1f}%)")
print(f"   Note: Some steps lack screenshots in original Mind2Web data")

print(f"\n" + "="*70)
print(f"✅ DATASET GENERATION SUCCESSFUL!")
print(f"="*70)
