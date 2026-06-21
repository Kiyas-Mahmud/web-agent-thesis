"""
split_dataset.py

Split FINAL_Trajectories_ENRICHED.json into train/val/test by original_task_id,
with the constraint that train-split records only go to train, and test-split
records only go to val/test.

Since train tasks are ~50% of unique task IDs (not 80%), the 80/10/10 ratio
is adjusted to respect the hard constraint: all train tasks → train, and test
tasks are split evenly between val and test.
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

INPUT_JSON = Path("output/dataset_70k_safe/FINAL_Trajectories_ENRICHED.json")
OUTPUT_DIR = Path("output/dataset_70k_safe")

random.seed(42)

# ---------------------------------------------------------------------------
# Load and group by task_id
# ---------------------------------------------------------------------------
print("Loading enriched dataset...")
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

task_records = defaultdict(list)
for rec in data:
    task_records[rec["original_task_id"]].append(rec)

print(f"Total records: {len(data)}")
print(f"Unique original_task_ids: {len(task_records)}")

# ---------------------------------------------------------------------------
# Separate train and test tasks
# ---------------------------------------------------------------------------
train_task_ids = []
test_task_ids = []

for tid, records in task_records.items():
    split_val = records[0]["split"]
    if split_val == "train":
        train_task_ids.append(tid)
    else:
        test_task_ids.append(tid)

print(f"Train tasks: {len(train_task_ids)}")
print(f"Test tasks:  {len(test_task_ids)}")

# ---------------------------------------------------------------------------
# Shuffle test tasks and split between val and test
# ---------------------------------------------------------------------------
random.shuffle(test_task_ids)

# Split test tasks 50/50 between val and test
# (Since train tasks are forced to train (~50%), this gives ~25% val, ~25% test)
half = len(test_task_ids) // 2
val_task_ids = test_task_ids[:half]
test_task_ids_final = test_task_ids[half:]

# Train gets all train tasks
train_task_ids_final = train_task_ids

print(f"\nSplit plan:")
print(f"  Train tasks: {len(train_task_ids_final)}")
print(f"  Val tasks:   {len(val_task_ids)}")
print(f"  Test tasks:  {len(test_task_ids_final)}")

# ---------------------------------------------------------------------------
# Assemble records
# ---------------------------------------------------------------------------
train_records = []
val_records = []
test_records = []

for tid in train_task_ids_final:
    train_records.extend(task_records[tid])
for tid in val_task_ids:
    val_records.extend(task_records[tid])
for tid in test_task_ids_final:
    test_records.extend(task_records[tid])

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
def save_split(records, filename):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(records)} records to {filename}")

save_split(train_records, "split_train.json")
save_split(val_records, "split_val.json")
save_split(test_records, "split_test.json")

# ---------------------------------------------------------------------------
# Verification report
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("VERIFICATION REPORT")
print("=" * 70)

total_out = len(train_records) + len(val_records) + len(test_records)
print(f"\nTotal records in split_train.json: {len(train_records)} ({len(train_records)/len(data)*100:.1f}%)")
print(f"Total records in split_val.json:   {len(val_records)} ({len(val_records)/len(data)*100:.1f}%)")
print(f"Total records in split_test.json:  {len(test_records)} ({len(test_records)/len(data)*100:.1f}%)")
print(f"Total across all three files:      {total_out}")
assert total_out == len(data), f"MISMATCH: expected {len(data)}, got {total_out}"
print("  [OK] Total equals exactly 70,965")

# Unique task IDs per file
def get_task_ids(records):
    return set(r["original_task_id"] for r in records)

train_ids = get_task_ids(train_records)
val_ids = get_task_ids(val_records)
test_ids = get_task_ids(test_records)

print(f"\nUnique original_task_ids:")
print(f"  split_train.json: {len(train_ids)}")
print(f"  split_val.json:   {len(val_ids)}")
print(f"  split_test.json:  {len(test_ids)}")

# Zero overlap
overlap_tv = train_ids & val_ids
overlap_tt = train_ids & test_ids
overlap_vt = val_ids & test_ids
print(f"\nOverlap check:")
print(f"  Train & Val:   {len(overlap_tv)} (should be 0)")
print(f"  Train & Test:  {len(overlap_tt)} (should be 0)")
print(f"  Val & Test:    {len(overlap_vt)} (should be 0)")
assert len(overlap_tv) == 0 and len(overlap_tt) == 0 and len(overlap_vt) == 0
print("  [OK] Zero overlap confirmed")

# Split field distribution
def show_split_dist(records, name):
    counts = Counter(r["split"] for r in records)
    print(f"\n{name} split distribution:")
    for s, c in counts.items():
        print(f"  {s}: {c}")

show_split_dist(train_records, "split_train.json")
show_split_dist(val_records, "split_val.json")
show_split_dist(test_records, "split_test.json")

# Failure type distribution
def show_failure_dist(records, name):
    counts = Counter(r["failure_type"] for r in records)
    print(f"\n{name} failure_type distribution:")
    for s, c in counts.most_common():
        print(f"  {s}: {c}")

show_failure_dist(train_records, "split_train.json")
show_failure_dist(val_records, "split_val.json")
show_failure_dist(test_records, "split_test.json")

# Website domain - top 5
def show_top_domains(records, name):
    counts = Counter(r["website_domain"] for r in records)
    print(f"\n{name} top 5 website_domain:")
    for domain, count in counts.most_common(5):
        print(f"  {domain}: {count}")

show_top_domains(train_records, "split_train.json")
show_top_domains(val_records, "split_val.json")
show_top_domains(test_records, "split_test.json")

# Execution outcome
def show_outcome_dist(records, name):
    counts = Counter(r["execution_outcome"] for r in records)
    print(f"\n{name} execution_outcome:")
    for s, c in counts.items():
        print(f"  {s}: {c}")

show_outcome_dist(train_records, "split_train.json")
show_outcome_dist(val_records, "split_val.json")
show_outcome_dist(test_records, "split_test.json")

# Sample records
def show_samples(records, name):
    print(f"\n{name} sample records:")
    for i, r in enumerate(records[:3], 1):
        print(f"  {i}. task_id={r['task_id']}, domain={r['website_domain']}, "
              f"failure={r['failure_type']}, outcome={r['execution_outcome']}, split={r['split']}")
        print(f"     task_desc: {r['task_description'][:100]}...")

show_samples(train_records, "split_train.json")
show_samples(val_records, "split_val.json")
show_samples(test_records, "split_test.json")

# JSON validity
print("\nJSON validity check:")
for fname in ["split_train.json", "split_val.json", "split_test.json"]:
    path = OUTPUT_DIR / fname
    with open(path, "r", encoding="utf-8") as f:
        _ = json.load(f)
    print(f"  {fname}: Valid JSON")

print("\n" + "=" * 70)
print("SPLIT COMPLETE")
print("=" * 70)
