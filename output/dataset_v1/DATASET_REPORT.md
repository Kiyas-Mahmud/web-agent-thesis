# Mind2Web Offline Augmentation Dataset Report

**Generated:** February 23, 2026  
**Dataset Location:** `E:\University\thesis\datacollection\output\dataset_10k_final`

---

## 📊 Executive Summary

This dataset contains **7,775 web navigation steps** from the Mind2Web dataset, augmented with synthetic failure scenarios for training robust web agents. The dataset includes both clean (successful) actions and augmented (failure) actions with detailed annotations and screenshots.

---

## 1. Dataset Overview

| Metric                           | Value         |
| -------------------------------- | ------------- |
| **Total Trajectories**           | 1,009         |
| **Total Steps (Rows)**           | 7,775         |
| **Clean Steps**                  | 3,117 (40.1%) |
| **Augmented Steps**              | 4,658 (59.9%) |
| **Average Steps per Trajectory** | 7.7           |
| **Total Dataset Size**           | ~1.27 GB      |
| **JSON Files Size**              | ~7.4 MB       |
| **Images Size**                  | ~1.26 GB      |

---

## 2. Labels & Annotations

### 2.1 Action Type Labels

The dataset contains 3 types of web interaction actions:

| Action Type | Count | Percentage | Description                                |
| ----------- | ----- | ---------- | ------------------------------------------ |
| **CLICK**   | 6,513 | 83.8%      | Click on an element (buttons, links, etc.) |
| **TYPE**    | 936   | 12.0%      | Enter text into input fields               |
| **SELECT**  | 326   | 4.2%       | Choose option from dropdown menu           |

**Total Steps:** 7,775 (all steps have action type labels)

### 2.2 Failure Type Labels (Augmented Data)

The dataset includes 5 types of synthetic failures:

| Failure Type        | Count | Percentage | Description                                  |
| ------------------- | ----- | ---------- | -------------------------------------------- |
| **TARGET_MISSING**  | 1,458 | 31.3%      | Target element not present in UI             |
| **WRONG_OPERATION** | 1,072 | 23.0%      | Incorrect action type used                   |
| **MISCLICK**        | 1,048 | 22.5%      | Clicked wrong element (nearby but incorrect) |
| **NO_STATE_CHANGE** | 761   | 16.3%      | Action executed but UI didn't respond        |
| **LOOP**            | 319   | 6.8%       | Agent stuck repeating same action            |

**Total:** 5/5 failure types present ✅

---

## 3. Image Data

### 3.1 Image Statistics

| Metric                  | Value                          |
| ----------------------- | ------------------------------ |
| **Total Image Folders** | 1,009 (task_0000 to task_1008) |
| **Total Image Files**   | 14,226                         |
| **Expected Images**     | 15,550 (2 per step)            |
| **Missing Images**      | 1,324 (8.5%)                   |
| **Image Success Rate**  | 91.5% ✅                       |

### 3.2 Image Availability

| Category                       | Count  | Percentage        |
| ------------------------------ | ------ | ----------------- |
| Steps with image paths in JSON | 7,775  | 100%              |
| Actual image files on disk     | 14,226 | 91.5% of expected |
| Steps with coordinates         | 7,362  | 94.7%             |

**Note:** All steps have image paths in the JSON, but 8.5% of image files are missing on disk because the original Mind2Web dataset lacked screenshots for those steps.

### 3.3 Image Specifications

- **Format:** JPEG (.jpg)
- **Resolution:** Variable (resized to max width 512px)
- **Quality:** 70% (compressed for efficiency)
- **Color Space:** RGB
- **Naming Convention:**
  - Before: `step_XXXX_before.jpg`
  - After: `step_XXXX_after.jpg`
- **Organization:** Grouped by task folders (task_0000 to task_1008)

### 3.4 Image Paths in JSON

Each step contains:

- `state_before_image`: Path to screenshot before action
- `state_after_image`: Path to screenshot after action

**Important:** Always check if image file exists before loading, as some paths point to non-existent files.

---

## 4. Data Structure

### 4.1 File Structure

```
output/dataset_10k_final/
├── augmented_trajectories.json    # Main dataset (7.4 MB)
├── summary.json                    # Statistics summary
├── DATASET_REPORT.md              # This report
└── images/                         # Screenshots (1.26 GB)
    ├── task_0000/                  # Task folder
    │   ├── step_0000_before.jpg
    │   ├── step_0000_after.jpg
    │   └── ...
    ├── task_0001/
    └── ...
```

### 4.2 JSON Schema

**Root Level:** Array of trajectory objects

**Trajectory Object:**

```json
{
  "task_id": "unique-task-identifier",
  "annotation_id": "mind2web-annotation-id",
  "steps": [ ... ]
}
```

**Step Object:**

```json
{
  "task_id": "task-identifier",
  "step_number": 0,
  "action_type": "CLICK|TYPE|SELECT|...",
  "action_target": "Element description",
  "action_coords": [x, y, width, height],
  "execution_outcome": "success|failure",
  "is_augmented": true|false,
  "injection_type": "TARGET_MISSING|WRONG_OPERATION|...",
  "failure_type": "Detailed failure category",
  "failure_subtype": "Specific failure variant",
  "root_cause": "Why the failure occurred",
  "recovery_strategy": "How to recover",
  "recovery_action": "Specific recovery steps",
  "recovery_success": true|false,
  "state_before_image": "images/task_XXXX/step_XXXX_before.jpg",
  "state_after_image": "images/task_XXXX/step_XXXX_after.jpg"
}
```

---

## 5. Quality Metrics

| Quality Gate               | Status  | Value | Target            |
| -------------------------- | ------- | ----- | ----------------- |
| **Augmentation Rate**      | ✅ PASS | 59.9% | 40-70%            |
| **LOOP Failure Rate**      | ✅ PASS | 6.8%  | ≥5%               |
| **Failure Type Coverage**  | ✅ PASS | 5/5   | All types present |
| **Duplicate Trajectories** | ✅ PASS | 0     | Zero duplicates   |
| **Null Labels**            | ✅ PASS | 0     | No missing labels |

**Overall Quality:** ✅ **ALL QUALITY GATES PASSED**

---

## 6. Dataset Usage

### 6.1 Loading the Dataset

**Python Example:**

```python
import json
from pathlib import Path
from PIL import Image

# Load dataset
dataset_path = Path('output/dataset_10k_final')
with open(dataset_path / 'augmented_trajectories.json', 'r') as f:
    data = json.load(f)

# Iterate through trajectories
for trajectory in data:
    print(f"Task: {trajectory['task_id']}")
    for step in trajectory['steps']:
        print(f"  - {step['action_type']} on {step['action_target']}")

        if step['is_augmented']:
            print(f"    Failure: {step['injection_type']}")

        # Load images (check if file exists first!)
        if step.get('state_before_image'):
            img_path = dataset_path / step['state_before_image']
            if img_path.exists():
                img = Image.open(img_path)
                # Process image...
            else:
                print(f"    Warning: Image missing - {img_path}")
```

**Key Points:**

- Always check if image file exists before loading (8.5% missing)
- Use `step.get('field')` to safely access optional fields
- Image paths are relative to dataset root directory

### 6.2 Recommended Data Splits

**Option 1: Split by Steps**

- Training: 70% (~5,442 steps)
- Validation: 15% (~1,166 steps)
- Testing: 15% (~1,167 steps)

**Option 2: Split by Trajectories (Recommended)**

- Training: 70% (~706 trajectories)
- Validation: 15% (~151 trajectories)
- Testing: 15% (~152 trajectories)

Splitting by trajectories keeps task sequences intact, which is better for evaluating sequential reasoning.

### 6.3 Filtering Data

**Get only clean (successful) steps:**

```python
clean_steps = [
    step for traj in data
    for step in traj['steps']
    if not step['is_augmented']
]
```

**Get only augmented (failure) steps:**

```python
failure_steps = [
    step for traj in data
    for step in traj['steps']
    if step['is_augmented']
]
```

**Filter by specific failure type:**

```python
misclick_steps = [
    step for traj in data
    for step in traj['steps']
    if step['injection_type'] == 'MISCLICK'
]
```

---

## 7. Research Applications

### 7.1 Potential Research Questions

1. **Failure Detection:** Can models learn to detect web UI failures from screenshots and action sequences?

2. **Failure Classification:** Which failure types are hardest to distinguish?

3. **Robustness Evaluation:** Does training with synthetic failures improve agent robustness?

4. **Multimodal Learning:** How important are visual features vs. textual features for failure detection?

5. **Recovery Planning:** Can models predict effective recovery actions?

### 7.2 Suggested Baselines

- **Vision-Language Models:** CLIP, BLIP, LLaVA for multimodal understanding
- **Action Prediction:** Behavioral cloning with failure augmentation
- **Sequence Models:** Transformers, LSTMs for trajectory modeling
- **Classification:** Binary (success/failure) or multi-class (failure types)

---

## 8. Limitations & Considerations

### 8.1 Known Limitations

1. **Missing Images (8.5%)**
   - Some steps lack screenshots due to original Mind2Web data
   - Does not affect label quality
   - Steps still have textual annotations

2. **Image Compression**
   - JPEG 70% quality for file size efficiency
   - Resized to 512px width for memory efficiency
   - May lose some visual detail

3. **Synthetic Failures**
   - Augmented failures are synthetic, may not perfectly match real failures
   - Balance controlled by injector probabilities
   - Real-world validation recommended

4. **Dataset Scope**
   - Only train split from Mind2Web used
   - Limited to web navigation tasks
   - English language websites only

### 8.2 Best Practices

✅ **DO:**

- Split by trajectories to preserve task sequences
- Use both visual and textual features
- Validate on real failure scenarios
- Report results on clean vs. augmented data separately

❌ **DON'T:**

- Mix trajectory steps across train/test splits
- Ignore missing images (handle None values)
- Assume failures are perfectly realistic
- Use only augmented data for training

---

## 9. Citation & Acknowledgments

### 9.1 Mind2Web Dataset

If you use this dataset, please cite the original Mind2Web paper:

```bibtex
@article{deng2023mind2web,
  title={Mind2web: Towards a generalist agent for the web},
  author={Deng, Xiang and Gu, Yu and Zheng, Boyuan and Chen, Shijie and Stevens, Samuel and Wang, Boshi and Sun, Huan and Su, Yu},
  journal={arXiv preprint arXiv:2306.06070},
  year={2023}
}
```

### 9.2 Dataset Source

- **Original Data:** osunlp/Multimodal-Mind2Web (HuggingFace)
- **Augmentation Pipeline:** Custom offline augmentation framework
- **License:** Follow Mind2Web dataset license terms

---

## 10. Technical Details

### 10.1 Generation Process

1. **Data Loading:** Mind2Web trajectories loaded from cache
2. **Batch Processing:** 20 trajectories per batch (memory-efficient)
3. **Augmentation:** 5 failure injectors applied with controlled probabilities
4. **Image Processing:** Screenshots resized and compressed
5. **Quality Control:** Automated quality gates validation

### 10.2 Generation Statistics

- **Processing Time:** ~2 hours
- **Memory Usage:** Peak ~4 GB RAM (16 GB available)
- **Batches Processed:** 51 batches
- **Total Duration:** ~2026-02-23 16:00 to 18:30

### 10.3 Reproducibility

To reproduce this dataset:

```bash
# Install dependencies
pip install -r requirements.txt

# Run generation script
python generate_10k_batch_fixed.py
```

Configuration used:

- Batch size: 20 trajectories
- Image width: 512px
- Image quality: 70%
- Random seed: 42
- Load screenshots: True

---

## 11. Contact & Support

### 11.1 Documentation

- **Details:** `docs/Details.md`
- **Generation Log:** `dataset_generation.log`
- **Validation Script:** `validate_10k_dataset.py`

### 11.2 Data Verification

Run validation:

```bash
python validate_10k_dataset.py
```

Generate fresh report:

```bash
python generate_dataset_report.py
```

---

## 12. Version History

| Version | Date       | Changes                                 |
| ------- | ---------- | --------------------------------------- |
| **1.0** | 2026-02-23 | Initial dataset generation              |
|         |            | - 7,775 steps from Mind2Web train split |
|         |            | - 59.9% augmentation rate               |
|         |            | - All 5 failure types present           |
|         |            | - 91.5% image success rate              |

---

## Summary Statistics

```
Dataset: Mind2Web Offline Augmentation v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Size:        1.27 GB
📊 Rows:        7,775 steps
🎯 Trajectories: 1,009 unique tasks
🖼️  Images:      14,226 files (91.5% coverage)
✨ Quality:     ALL GATES PASSED ✅

Failure Distribution:
  TARGET_MISSING    ████████████████████████████░░░ 31.3%
  WRONG_OPERATION   ███████████████████████░░░░░░░░ 23.0%
  MISCLICK         ██████████████████████░░░░░░░░░░ 22.5%
  NO_STATE_CHANGE  ████████████████░░░░░░░░░░░░░░░░ 16.3%
  LOOP            ███████░░░░░░░░░░░░░░░░░░░░░░░░░░  6.8%
```

---

**Dataset Ready for Q1 Journal Publication** 🎓📝

For questions or issues, refer to generation logs and validation scripts.

**Last Updated:** February 23, 2026
