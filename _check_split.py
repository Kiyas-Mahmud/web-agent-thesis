import json
from collections import Counter

with open('output/dataset_70k_safe/FINAL_Trajectories_ENRICHED.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

task_split = {}
for r in data:
    tid = r['original_task_id']
    if tid not in task_split:
        task_split[tid] = r['split']

counts = Counter(task_split.values())
print('Unique task_ids by split:')
for s, c in counts.items():
    print(f'  {s}: {c}')
total = sum(counts.values())
print(f'Total: {total}')
print(f'Train pct: {counts["train"] / total * 100:.1f}%')
