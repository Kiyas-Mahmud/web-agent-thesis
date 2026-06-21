"""
Diagnose all 3 problems in augmented_trajectories_FINAL_Update.json
"""
import json
from collections import Counter

INPUT = "output/dataset_70k_safe/augmented_trajectories_FINAL_Update.json"

print(f"Loading {INPUT}...")
with open(INPUT) as f:
    steps = json.load(f)

total = len(steps)
print(f"Total steps: {total:,}\n")

# ── Problem 1: Empty state_before ──
empty_before = [s for s in steps if not str(s.get("state_before", "")).strip()]
print(f"Problem 1 — Empty state_before: {len(empty_before)} steps")

# ── Problem 2: Gap analysis (70,965 → 60,810) ──
print(f"\nProblem 2 — Gap: 70,965 - {total} = {70965 - total} steps removed")
# Load the original to confirm what was removed
with open("output/dataset_70k_safe/augmented_trajectories.json") as f:
    original = json.load(f)
print(f"  Original raw: {len(original):,}")

# Count nulls in original
orig_null_after = sum(1 for s in original if s.get("state_after_path") is None or str(s.get("state_after_path","")).strip() == "")
orig_null_before = sum(1 for s in original if s.get("state_before_path") is None or str(s.get("state_before_path","")).strip() == "")
print(f"  Original null state_after_path: {orig_null_after}")
print(f"  Original null state_before_path: {orig_null_before}")
print(f"  Expected after filtering state_after: {len(original) - orig_null_after}")
print(f"  Actual FINAL_Update count: {total}")
match = (len(original) - orig_null_after) == total
print(f"  Match: {'YES - filtering was correct' if match else 'NO - investigate further'}")

# ── Problem 3: Action type distribution ──
print(f"\nProblem 3 — Action type distribution:")
action_counts = Counter(s.get("action_type", "UNKNOWN") for s in steps)
for atype, count in action_counts.most_common():
    pct = count / total * 100
    print(f"  {atype}: {count:,} ({pct:.1f}%)")

expected_types = {"CLICK", "TYPE", "SELECT", "SCROLL", "NAVIGATE"}
present_types = set(action_counts.keys())
missing_types = expected_types - present_types
if missing_types:
    print(f"  MISSING types: {missing_types}")
else:
    print(f"  All 5 action types present!")

# Also check original for these types
orig_actions = Counter(s.get("action_type", "UNKNOWN") for s in original)
print(f"\n  Action types in ORIGINAL (pre-filter):")
for atype, count in orig_actions.most_common():
    print(f"    {atype}: {count:,}")
