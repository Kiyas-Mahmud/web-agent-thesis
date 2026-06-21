# Multimodal Web Interaction Failure Dataset: Final Report

## 1. High-Level Summary
- **Dataset Name:** dataset_70k_safe
- **Total Web Interactions (Steps):** 70,965
- **Total Unique Trajectories/Tasks:** 2,022
- **Total Images:** 131,720 screenshots (256px, 60% JPEG)
- **Total Disk Size:** 3.18 GB
- **Data Source:** Mind2Web (HuggingFace) `train`, `test_domain`, `test_task`, `test_website` splits.

## 2. Dataset Generation Breakdown
The total 70,965 steps were generated across 5 randomized "passes". Each dataset split yielded the following counts over the combined passes:
- **`train` Split:** 38,875 steps
- **`test_domain` Split:** 20,300 steps
- **`test_task` Split:** 6,695 steps
- **`test_website` Split:** 5,095 steps

## 3. Failure Injection Distribution
Synthetic failures were safely injected at an overall ~72% injection rate to map against clean baseline examples. Over the 70,965 steps, the exact distribution of actions is:

| Step Outcome | Count | Percentage |
| :--- | :--- | :--- |
| **CLEAN (No Failure)** | **19,929** | **28.1%** |
| `TARGET_MISSING` | 18,043 | 25.4% |
| `WRONG_OPERATION` | 15,268 | 21.5% |
| `MISCLICK` | 12,470 | 17.6% |
| `LOOP` | 5,255 | 7.4% |

---

## 4. Flattened JSON Schema Definition
The dataset is serialized as a flattened array inside `augmented_trajectories.json`. Every dictionary in the array represents exactly **one step**, which is ideal for PyTorch or TensorFlow DataLoader iterations.

```json
{
  "task_id": "test_domain_pass4_013781df_3",
  "original_task_id": "013781df-4391-4533-bcb1-15f6819064f6",
  "split": "test_domain",
  "pass": "pass4",
  "annotation_id": "013781df-4391-4533-bcb1-15f6819064f6",
  "action_type": "CLICK",
  "action_target": "element_3",
  "action_target_bbox": {
    "height": 24.0, 
    "width": 105.0, 
    "x": 25.0, 
    "y": 142.5
  },
  "state_before_path": "images\\test_domain_pass4_013781df\\step_0003_before.jpg",
  "state_after_path": "images\\test_domain_pass4_013781df\\step_0003_after.jpg",
  "is_augmented": true,
  "injection_type": "MISCLICK",
  "failure_reason": "Clicked adjacent element instead of target",
  "recovery_action": "REPLAN"
}
```

### 4.1. Schema Field Reference
> **NOTE:** If `is_augmented` is `false`, the injection fields (`injection_type`, `failure_reason`, `recovery_action`) will be `null`.

*   **`task_id`**: A unique string for this exact step (combining split, pass, task ID, and step number).
*   **`original_task_id`**: The original trajectory UUID from the Mind2Web benchmark.
*   **`split`**: The data split it originated from (`train`, `test_domain`, etc.)
*   **`pass`**: Which randomized generation string produced this step (`pass1` to `pass5`).
*   **`action_type`**: The type of web interaction (e.g., `CLICK`, `TYPE`, `SELECT`).
*   **`action_target_bbox`**: The X, Y, Width, and Height coordinates of the target UI element on the browser.
*   **`state_before_path` & `state_after_path`**: Relative paths pointing to the UI screenshot before and after the action is executed.
*   **`is_augmented`**: A boolean `true/false` flag. Evaluates cleanly whether the row contains a synthetic failure.
*   **`injection_type`**: The specific class label of the failure (e.g., `MISCLICK`). Used for supervised classification training.
*   **`failure_reason`**: Natural language justification for the failure context (useful for Language Model Context).
*   **`recovery_action`**: Suggested strategy for recovery (`REPLAN`, `SCROLL_AND_RETRY`, etc.).

---

## 5. Duplicate Handling & Quality Gates
* **Data Overlap Avoidance:** The prototype dataset `dataset_v1` exists completely localized inside this dataset. The prototype format was nested. The 70k safe dataset contains its data entirely flattened. Therefore, `dataset_v1` is deprecated and **must not be merged** to prevent duplicate leakage in training sets.
* **Resolution Control:** All images have been downscaled utilizing Lanczos resampling to clamp file memory (width 256px), avoiding the 131,000+ files bottlenecking memory limits scaling past datasets.
