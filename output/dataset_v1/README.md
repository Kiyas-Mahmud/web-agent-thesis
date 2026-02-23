# Mind2Web Offline Augmentation Dataset

**Version:** 1.0  
**Generated:** February 23, 2026  
**Size:** 1.27 GB

---

## 🎯 Quick Stats

- **7,775** data rows (steps)
- **1,009** unique trajectories
- **59.9%** augmentation rate
- **91.5%** image coverage
- **100%** quality gates passed ✅

---

## 📁 Files

| File                          | Size    | Description                         |
| ----------------------------- | ------- | ----------------------------------- |
| `augmented_trajectories.json` | 7.4 MB  | Main dataset with all steps         |
| `summary.json`                | <1 MB   | Summary statistics                  |
| `detailed_statistics.json`    | <1 MB   | Detailed analysis results           |
| `DATASET_REPORT.md`           | -       | **Full documentation (READ THIS!)** |
| `images/`                     | 1.26 GB | 14,226 screenshots in 1,009 folders |

---

## 🏷️ Labels

### Action Types (3)

- **CLICK** (83.8%) - Click elements
- **TYPE** (12.0%) - Enter text
- **SELECT** (4.2%) - Choose from dropdown

### Failure Types (5)

- **TARGET_MISSING** (31.3%) - Element not present
- **WRONG_OPERATION** (23.0%) - Wrong action type
- **MISCLICK** (22.5%) - Clicked wrong element
- **NO_STATE_CHANGE** (16.3%) - No UI response
- **LOOP** (6.8%) - Repeated actions

---

## 🚀 Quick Start

```python
import json
from pathlib import Path

# Load dataset
with open('augmented_trajectories.json', 'r') as f:
    data = json.load(f)

# Print first trajectory
traj = data[0]
print(f"Task: {traj['task_id']}")
print(f"Steps: {len(traj['steps'])}")

# Print first step
step = traj['steps'][0]
print(f"Action: {step['action_type']}")
print(f"Target: {step['action_target']}")
print(f"Augmented: {step['is_augmented']}")
```

---

## ⚠️ Important Notes

1. **Missing Images:** 8.5% of image files are missing (original data limitation)
   - Always check if file exists before loading
   - All steps still have textual annotations

2. **Image Quality:** Compressed to 70% JPEG, 512px width for efficiency

3. **Data Split:** Recommended to split by trajectories, not individual steps

4. **Coordinates:** 94.7% of steps have bounding box coordinates

---

## 📖 Full Documentation

**Read the complete report:** [`DATASET_REPORT.md`](DATASET_REPORT.md)

Includes:

- Detailed statistics
- Data structure explanation
- Usage examples
- Research applications
- Citation information
- Quality metrics

---

## ✅ Quality Assurance

| Metric            | Value | Status             |
| ----------------- | ----- | ------------------ |
| Augmentation Rate | 59.9% | ✅ (40-70% target) |
| LOOP Failures     | 6.8%  | ✅ (≥5% required)  |
| Failure Coverage  | 5/5   | ✅ (All types)     |
| Duplicates        | 0     | ✅ (None)          |
| Null Labels       | 0     | ✅ (None)          |

---

## 📚 Citation

If you use this dataset, please cite:

```bibtex
@article{deng2023mind2web,
  title={Mind2web: Towards a generalist agent for the web},
  author={Deng, Xiang and others},
  journal={arXiv preprint arXiv:2306.06070},
  year={2023}
}
```

---

**Dataset ready for Q1 journal publication!** 🎓

For questions, see generation logs or contact thesis supervisor.
