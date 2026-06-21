# Task-07: Data Cleaning & Splitting

**Phase:** 7  
**Priority:** 🟡 Medium  
**Status:** ⬜ Not Started  
**Estimated Duration:** 1 week  
**Assigned To:** [Your Name]  
**Start Date:** -  
**Completion Date:** -

---

## 1. Objective

Implement data cleaning, validation, and splitting pipelines to produce train/validation/test splits with proper domain awareness, balanced failure distribution, and schema validation.

---

## 2. Deliverables

### 2.1 Data Cleaning Pipeline

- [ ] Duplicate detection and removal
- [ ] Incomplete trajectory filtering
- [ ] Schema validation
- [ ] Anomaly detection

### 2.2 Data Validation

- [ ] JSON schema validation
- [ ] Image file verification
- [ ] Trajectory consistency checks
- [ ] Metadata completeness

### 2.3 Dataset Splitting

- [ ] Domain-aware split
- [ ] Stratified failure distribution
- [ ] 70/15/15 train/val/test split
- [ ] No data leakage validation

### 2.4 Statistics & Reporting

- [ ] Dataset statistics report
- [ ] Failure distribution analysis
- [ ] Domain coverage report
- [ ] Quality metrics

---

## 3. Technical Specifications

### 3.1 Split Configuration

```python
SPLIT_CONFIG = {
    "train_ratio": 0.70,
    "val_ratio": 0.15,
    "test_ratio": 0.15,
    "stratify_by": ["domain", "failure_type"],
    "min_samples_per_domain": 10,
    "ensure_recovery_pairs": True
}
```

### 3.2 Validation Rules

```python
VALIDATION_RULES = {
    "required_fields": [
        "task_id", "step_id", "action_type",
        "screenshot_before", "screenshot_after",
        "execution_outcome", "failure_type"
    ],
    "image_extensions": [".png"],
    "max_trajectory_length": 100,
    "min_trajectory_length": 3,
    "valid_action_types": [
        "CLICK", "TYPE", "SCROLL", "SELECT", "NAVIGATE"
    ]
}
```

### 3.3 DataCleaner API

```python
class DataCleaner:
    def validate_schema(self, record: Dict) -> bool
    def check_image_exists(self, path: str) -> bool
    def detect_duplicates(self, records: List[Dict]) -> List[int]
    def filter_incomplete(self, records: List[Dict]) -> List[Dict]
    def compute_statistics(self, records: List[Dict]) -> Dict
    def split_dataset(self, records: List[Dict]) -> Tuple[List, List, List]
```

---

## 4. Implementation Steps

### Step 1: Schema Validation (Days 1-2)

- [ ] Define JSON schema
- [ ] Implement validator
- [ ] Test on sample data
- [ ] Generate validation report

### Step 2: Data Cleaning (Days 2-3)

- [ ] Duplicate detection logic
- [ ] Incomplete trajectory filtering
- [ ] Anomaly detection
- [ ] Cleaning report

### Step 3: Image Verification (Day 3)

- [ ] Check file existence
- [ ] Verify image integrity
- [ ] Resolution validation
- [ ] Storage audit

### Step 4: Dataset Splitting (Days 4-5)

- [ ] Domain extraction
- [ ] Stratified sampling
- [ ] Split generation
- [ ] Leakage prevention checks

### Step 5: Statistics & Reporting (Days 6-7)

- [ ] Compute dataset statistics
- [ ] Generate distribution plots
- [ ] Create quality report
- [ ] Export split metadata

---

## 5. Cleaning Criteria

### Remove if:

- Missing required fields
- Screenshot files not found
- Trajectory length < 3 steps
- Duplicate task_id
- Invalid action types
- Corrupted images

### Flag for review if:

- Trajectory length > 50 steps
- All steps marked as failures
- No state changes detected
- Extremely high failure rate (>80%)

---

## 6. Splitting Strategy

### Domain-Aware Split

1. Group tasks by domain
2. Ensure each domain appears in all splits
3. Maintain proportions within domains

### Failure Distribution

- Balance failure types across splits
- Ensure each split has representative failures
- Keep failure-recovery pairs together

### Example Distribution Target:

```
Train:   70% of data, all domains, all failure types
Val:     15% of data, all domains, all failure types
Test:    15% of data, all domains, all failure types
```

---

## 7. Dependencies

### External Dependencies

- jsonschema (for validation)
- pandas (for analysis)
- matplotlib/seaborn (for visualization)

### Internal Dependencies

- All previous tasks (for complete dataset)

---

## 8. Success Criteria

✅ **Task complete when:**

1. All data validated against schema
2. Clean dataset with no duplicates
3. Train/val/test splits generated
4. No data leakage between splits
5. Statistics report generated
6. Documentation complete

---

## 9. Testing Checklist

- [ ] Validate 1000+ records
- [ ] Verify image file consistency
- [ ] Check split proportions
- [ ] Validate domain distribution
- [ ] Verify failure type balance
- [ ] Test for data leakage

---

## 10. Quality Metrics

```python
QUALITY_METRICS = {
    "completeness": "% records with all required fields",
    "consistency": "% trajectories with valid action sequences",
    "image_quality": "% images with correct resolution",
    "failure_coverage": "# unique failure types",
    "domain_coverage": "# unique domains",
    "recovery_rate": "% failures with recovery attempts"
}
```

---

## 11. Output Structure

```
dataset/
├── splits/
│   ├── train.jsonl          # Training split
│   ├── val.jsonl            # Validation split
│   ├── test.jsonl           # Test split
│   └── metadata.json        # Split statistics
├── stats/
│   ├── dataset_report.md    # Full statistics
│   ├── failure_dist.png     # Distribution plots
│   └── domain_coverage.png
└── validation/
    ├── validation_log.txt
    └── cleaned_ids.txt
```

---

## 12. Statistics Report Template

```markdown
# Dataset Statistics Report

## Overview

- Total tasks: X
- Total steps: Y
- Date range: A - B
- Domains: Z

## Split Distribution

- Train: X tasks, Y steps
- Val: X tasks, Y steps
- Test: X tasks, Y steps

## Failure Distribution

- Total failures: X (Y%)
- Failure types: [distribution]
- Recovery attempts: X (Y%)
- Recovery success: X (Y%)

## Domain Coverage

- [Domain distribution table]

## Quality Metrics

- Completeness: X%
- Consistency: Y%
- Image quality: Z%
```

---

## 13. Risk & Mitigation

| Risk              | Mitigation                           |
| ----------------- | ------------------------------------ |
| Data leakage      | Strict domain separation, validation |
| Imbalanced splits | Stratified sampling, minimum samples |
| Missing images    | Pre-flight checks, cleanup scripts   |

---

## 14. Progress Log

### 2026-02-19

- Task file created
- Status: Not Started
- Blocked by: Task-06 completion

---

## 15. Notes

- Run validation early and often
- Keep original data separate from cleaned data
- Document all cleaning decisions
- Generate versioned dataset releases

---

**Last Updated:** February 19, 2026  
**Next Review:** April 9, 2026
