import json
from collections import Counter
import statistics

file_path = 'output/dataset_70k_safe/final_trajectories_Enriched.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

total_steps = len(data)

splits = Counter()
passes = Counter()
outcomes = Counter()
failure_types = Counter()
action_types = Counter()
domains = Counter()
augmented_count = 0
injection_types = Counter()

diff_scores = []
confidence_scores = []

for step in data:
    splits[step.get('split', 'unknown')] += 1
    passes[step.get('pass', 'unknown')] += 1
    outcomes[step.get('execution_outcome', 'unknown')] += 1
    
    if step.get('execution_outcome') == 'FAILURE':
        failure_types[step.get('failure_type', 'unknown')] += 1
        
    action_types[step.get('action_type', 'unknown')] += 1
    domains[step.get('website_domain', 'unknown')] += 1
    
    if step.get('is_augmented'):
        augmented_count += 1
        injection_types[step.get('injection_type', 'unknown')] += 1
        
    if step.get('visual_diff_score') is not None:
        diff_scores.append(step.get('visual_diff_score'))
        
    if step.get('failure_confidence') is not None:
        confidence_scores.append(step.get('failure_confidence'))

print(f"Total Steps: {total_steps}")
print(f"Augmented Steps: {augmented_count}")

print("\n--- Splits ---")
for k, v in splits.most_common():
    print(f"- {k}: {v}")

print("\n--- Passes ---")
for k, v in passes.most_common():
    print(f"- {k}: {v}")

print("\n--- Execution Outcomes ---")
for k, v in outcomes.most_common():
    print(f"- {k}: {v}")

print("\n--- Failure Types (When FAILURE) ---")
for k, v in failure_types.most_common():
    print(f"- {k}: {v}")

print("\n--- Action Types ---")
for k, v in action_types.most_common():
    print(f"- {k}: {v}")

print("\n--- Top 10 Domains ---")
for k, v in domains.most_common(10):
    print(f"- {k}: {v}")

print("\n--- Injection Types ---")
for k, v in injection_types.most_common():
    print(f"- {k}: {v}")

print("\n--- Metrics ---")
print(f"- Average Visual Diff Score: {statistics.mean(diff_scores):.4f}" if diff_scores else "N/A")
print(f"- Average Failure Confidence: {statistics.mean(confidence_scores):.4f}" if confidence_scores else "N/A")

