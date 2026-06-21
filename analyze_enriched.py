import json
import os
from collections import Counter

file_path = 'output/dataset_70k_safe/final_trajectories_Enriched.json'

def analyze_dataset(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    print(f"Analyzing {path}...\n")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Total trajectories: {len(data)}")
    
    total_steps = 0
    domains = Counter()
    websites = Counter()
    sources = Counter()
    outcomes = Counter()
    step_outcomes = Counter()
    
    for traj in data:
        traj_steps = traj.get('steps', [])
        total_steps += len(traj_steps)
        domains[traj.get('domain', 'unknown')] += 1
        websites[traj.get('website', 'unknown')] += 1
        sources[traj.get('source_dataset', 'unknown')] += 1
        outcomes[traj.get('gold_outcome', 'unknown')] += 1
        
        for step in traj_steps:
            step_outcomes[step.get('action_type', 'unknown')] += 1
            
    print(f"Total steps: {total_steps}")
    print("\n--- Sources Distribution ---")
    for k, v in sources.most_common():
        print(f"{k}: {v}")
        
    print("\n--- Trajectory Outcomes ---")
    for k, v in outcomes.most_common():
        print(f"{k}: {v}")
        
    print("\n--- Top 10 Domains ---")
    for k, v in domains.most_common(10):
        print(f"{k}: {v}")
        
    print("\n--- Top 10 Websites ---")
    for k, v in websites.most_common(10):
        print(f"{k}: {v}")
        
    print("\n--- Action Types in Steps ---")
    for k, v in step_outcomes.most_common():
        print(f"{k}: {v}")

if __name__ == '__main__':
    analyze_dataset(file_path)
