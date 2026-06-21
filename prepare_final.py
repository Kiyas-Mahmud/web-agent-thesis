"""
Fix 1: Removes steps with empty state_after paths.
Fix 2: Translates 'element_N' descriptions to semantic components using logical heuristics.

Input: output/dataset_70k_safe/augmented_trajectories_READY.json
Output: output/dataset_70k_safe/augmented_trajectories_FINAL_Update.json
"""

import json
import sys

def main():
    input_path = "output/dataset_70k_safe/augmented_trajectories_READY.json"
    output_path = "output/dataset_70k_safe/augmented_trajectories_FINAL_Update.json"
    
    print(f"Loading {input_path}...")
    with open(input_path) as f:
        steps = json.load(f)

    # Fix 1 — remove steps with empty state_after or state_before
    steps = [s for s in steps if str(s.get("state_after", "")).strip() != "" and str(s.get("state_before", "")).strip() != ""]
    print(f"Removed {before - after} steps with missing state_after")

    # Fix 2 — enrich action_target_desc using bbox context
    for s in steps:
        desc = str(s.get("action_target_desc", ""))
        
        # Check if it looks like the raw element_N IDs
        if desc.startswith("element_") or desc.strip() == "":
            action = s.get("action_type", "CLICK").lower()
            
            # The preparation script retained the 'action_target_bbox' inside our READY json explicitly
            bbox = s.get("action_target_bbox", {})
            
            # Handle cases where bbox is missing/none
            if not isinstance(bbox, dict):
                bbox = {}
                
            w = float(bbox.get("width", 0) or 0)
            h = float(bbox.get("height", 0) or 0)
            
            # Basic fallback coordinates
            coords = s.get("action_coordinates", [512, 384])

            # Guess element type from size and action
            if action == "type":
                s["action_target_desc"] = "text input field"
            elif w > 200 and h > 40:
                s["action_target_desc"] = "large button or link"
            elif w < 50 and h < 50:
                s["action_target_desc"] = "small icon or checkbox"
            elif action == "select":
                s["action_target_desc"] = "dropdown selector"
            else:
                s["action_target_desc"] = f"clickable element at ({int(coords[0])}, {int(coords[1])})"

    with open(output_path, "w") as f:
        json.dump(steps, f, indent=2)

    print(f"Final dataset: {len(steps):,} steps")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    main()
