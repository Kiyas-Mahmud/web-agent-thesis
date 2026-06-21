"""
Validate 10K dataset quality - check for duplicates and quality gates
"""
import json
from collections import Counter
from pathlib import Path

print("="*80)
print("10K DATASET VALIDATION REPORT")
print("="*80)

# Load summary
summary_file = Path('output/dataset_10k_final/summary.json')
if not summary_file.exists():
    print("❌ summary.json not found - generation may not be complete")
    exit(1)

with open(summary_file, 'r') as f:
    summary = json.load(f)

# Load full dataset
data_file = Path('output/dataset_10k_final/augmented_trajectories.json')
with open(data_file, 'r') as f:
    data = json.load(f)

print(f"\n📊 DATASET OVERVIEW:")
print(f"   Total Trajectories: {summary['total_trajectories']}")
print(f"   Total Steps: {summary['total_steps']}")
print(f"   Avg Steps/Trajectory: {summary['avg_steps_per_trajectory']:.1f}")
print(f"   Clean Steps: {summary['clean_steps']} ({summary['clean_steps']/summary['total_steps']*100:.1f}%)")
print(f"   Augmented Steps: {summary['augmented_steps']} ({summary['augmented_steps']/summary['total_steps']*100:.1f}%)")

# Check for duplicates
print(f"\n🔍 DUPLICATE CHECK:")
task_ids = [t['task_id'] for t in data]
unique_task_ids = set(task_ids)
duplicate_count = len(task_ids) - len(unique_task_ids)

if duplicate_count == 0:
    print(f"   ✅ NO DUPLICATES: {len(unique_task_ids)} unique trajectories")
else:
    print(f"   ❌ DUPLICATES FOUND: {duplicate_count} duplicates out of {len(task_ids)} trajectories")
    # Show which task IDs are duplicated
    task_id_counts = Counter(task_ids)
    duplicated = {tid: count for tid, count in task_id_counts.items() if count > 1}
    print(f"   Duplicated task IDs: {len(duplicated)}")
    for tid, count in list(duplicated.items())[:5]:
        print(f"      {tid}: appears {count} times")

# Quality gates
print(f"\n✅ QUALITY GATE VALIDATION:")
aug_rate = summary['augmented_steps'] / summary['total_steps'] * 100
gate1 = "✅ PASS" if 40 <= aug_rate <= 70 else "❌ FAIL"
print(f"   {gate1} Augmentation Rate: {aug_rate:.1f}% (target: 40-70%)")

loop_count = summary['failure_distribution'].get('LOOP', 0)
loop_pct = (loop_count / summary['augmented_steps'] * 100) if summary['augmented_steps'] > 0 else 0
gate2 = "✅ PASS" if loop_pct >= 5.0 else "❌ FAIL"
print(f"   {gate2} LOOP Failures: {loop_count} ({loop_pct:.1f}% of augmented, threshold: ≥5%)")

gate3 = "✅ PASS" if len(summary['failure_distribution']) == 5 else "❌ FAIL"
print(f"   {gate3} All Failure Types Present: {len(summary['failure_distribution'])}/5")

gate4 = "✅ PASS" if duplicate_count == 0 else "❌ FAIL"
print(f"   {gate4} No Duplicates: {len(unique_task_ids)} unique / {len(data)} total")

target_reached = "✅ PASS" if summary['total_steps'] >= 10000 else "⚠️ PARTIAL"
print(f"   {target_reached} Target Steps: {summary['total_steps']}/10000")

# Failure distribution
print(f"\n🎯 FAILURE INJECTION DISTRIBUTION:")
for ft, count in sorted(summary['failure_distribution'].items(), key=lambda x: -x[1]):
    pct = count / summary['augmented_steps'] * 100
    print(f"   {ft:20s}: {count:4d} ({pct:5.1f}%)")

# Check for null data
print(f"\n🔧 NULL DATA CHECK:")
null_count = 0
for t in data[:10]:  # Sample first 10 trajectories
    for s in t['steps']:
        if s.get('action_type') is None or s.get('execution_outcome') is None:
            null_count += 1

if null_count == 0:
    print(f"   ✅ No null data in sample (first 10 trajectories)")
else:
    print(f"   ⚠️ Found {null_count} steps with null data in sample")

# Image check
img_dir = Path('output/dataset_10k_final/images')
if img_dir.exists():
    jpg_files = list(img_dir.rglob('*.jpg'))
    total_img_size = sum(f.stat().st_size for f in jpg_files) / (1024 * 1024 * 1024)
    avg_img_size = (sum(f.stat().st_size for f in jpg_files) / len(jpg_files)) / 1024 if jpg_files else 0
    
    print(f"\n📁 DATASET FILES:")
    json_size = data_file.stat().st_size / (1024 * 1024)
    print(f"   augmented_trajectories.json: {json_size:.2f} MB")
    print(f"   Images: {len(jpg_files)} files ({total_img_size:.2f} GB)")
    print(f"   Avg Image Size: {avg_img_size:.1f} KB")
    print(f"   Total Dataset Size: {json_size/1024 + total_img_size:.2f} GB")

# Final verdict
print("\n" + "="*80)
all_pass = (40 <= aug_rate <= 70) and (loop_pct >= 5.0) and len(summary['failure_distribution']) == 5 and duplicate_count == 0
if all_pass and summary['total_steps'] >= 10000:
    print("✅ DATASET GENERATION SUCCESSFUL!")
    print("   All quality gates passed")
    print("   No duplicates found")
    print("   Target 10K steps reached")
    print("   Ready for baseline model training")
elif all_pass:
    print("⚠️ DATASET GENERATION PARTIAL SUCCESS")
    print("   All quality gates passed")
    print("   No duplicates found")
    print(f"   Only {summary['total_steps']}/10K steps (dataset size limit)")
    print("   Ready for baseline model training")
else:
    print("❌ DATASET GENERATION INCOMPLETE")
    print("   Some quality gates failed - review needed")
print("="*80)
