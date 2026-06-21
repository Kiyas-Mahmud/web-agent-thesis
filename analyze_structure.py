import json

file_path = 'output/dataset_70k_safe/final_trajectories_Enriched.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

if data:
    first = data[0]
    print(f"Keys in first element: {list(first.keys())}")
    
    # Just print the first element formatted to see the structure
    import pprint
    # We might have nested structures, let's just print a truncated version of the values
    summary = {k: type(v).__name__ for k, v in first.items()}
    print(f"Structure types: {summary}")
    
    # Let's show the first level values (if string, truncate)
    for k, v in first.items():
        if isinstance(v, str) and len(v) > 100:
            print(f"{k}: {v[:100]}...")
        elif isinstance(v, list) and len(v) > 0:
            print(f"{k}: list of {len(v)} elements, first element type: {type(v[0]).__name__}")
            if isinstance(v[0], dict):
                print(f"  First element keys: {list(v[0].keys())}")
        else:
            print(f"{k}: {v}")
