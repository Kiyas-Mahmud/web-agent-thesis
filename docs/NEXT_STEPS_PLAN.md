# Next Steps Plan - Failure-Aware Dataset

**Date Created**: February 21, 2026  
**Current Status**: Pilot dataset complete (86 trajectories, 547 steps, 59.4% failure rate)  
**Goal**: Scale to full production dataset and prepare for Q1 journal submission

---

## 🎯 Core Objectives

### Primary Goals (MUST Complete for Q1 Submission):

1. ✅ **Enable and Validate LOOP Failure Injection** → Complete all 5 failure types
2. ✅ **Implement Quality Gate Before Scaling** → Prevent bad data at scale
3. ✅ **Scale to Full Dataset (500-1,000 tasks)** → Production-ready dataset
4. ✅ **Comprehensive Quality Assurance** → Validate at scale
5. ✅ **Build Baseline Models** → Prove dataset is learnable (CRITICAL for Q1)
6. ✅ **Complete Documentation & Dataset Card** → Make dataset public-ready
7. ✅ **Write Q1 Journal Paper** → Publish results

### Success Criteria:

- All 5 failure types operational (including LOOP ≥5%)
- Quality gate passes at pilot AND full scale
- Baseline accuracy >60% (proves learnability)
- Comprehensive documentation
- Paper ready for submission

---

## 📋 Step-by-Step Action Plan

**Logical Workflow**: Fix LOOP → Validate Pilot → Scale Up → Validate Again → Baselines → Document → Publish

### **Phase 1: Quality Gate Implementation** 🚦

**Priority**: CRITICAL  
**Duration**: 1-2 days  
**Purpose**: Ensure pilot quality before scaling

#### Tasks:

1. **Create validation script** (`scripts/validate_quality_gate.py`)
   - Check failure rate: 40-60%
   - Check LOOP presence: ≥5%
   - Check recovery success: >0%
   - Check data completeness: no missing screenshots/fields
   - Check schema validity: all required fields present

2. **Define quality metrics**

   ```python
   QualityGate:
     - failure_rate: [0.40, 0.60]
     - loop_percentage: ≥ 0.05
     - recovery_rate: > 0.0
     - missing_screenshots: 0
     - invalid_steps: 0
     - schema_violations: 0
   ```

3. **Implement automated check**
   - Run on pilot dataset (output/pilot_100_final/)
   - Generate quality report
   - Pass/Fail decision for scaling

4. **Create quality dashboard**
   - HTML report with charts
   - Per-injector statistics
   - Distribution visualizations
   - Error listings

#### Deliverables:

- ✅ `scripts/validate_quality_gate.py`
- ✅ `output/pilot_100_final/quality_report.html`
- ✅ Pass/Fail status for scaling

#### Acceptance Criteria:

- [ ] All quality gates pass on pilot dataset
- [ ] Report clearly shows metrics and thresholds
- [ ] Script can be reused for full dataset

---

### **Phase 2: LOOP Injector Completion** 🔄

**Priority**: HIGH  
**Duration**: 1 day  
**Dependency**: Required for Phase 1 quality gate

#### Tasks:

1. **Implement state_after loading**
   - Modify `_parse_single_action_step()` to load next screenshot
   - Handle last step (no state_after)
   - Memory optimization (load only when needed)

2. **Complete LOOP detection logic**
   - Compare state_before with previous step's state_after
   - Use SSIM threshold (>0.95 = same state)
   - Detect repeated action patterns
   - Require 2+ previous steps for context

3. **Implement LOOP injection**
   - Repeat last 2-3 actions
   - Keep states identical (simulate stuck UI)
   - Generate recovery: "try_different_approach"
   - Target: 13% of injections (config weight)

4. **Test LOOP injector**
   - Run on 20-task sample
   - Verify ≥5% LOOP failures
   - Check recovery hints
   - Validate no crashes

#### Deliverables:

- ✅ Updated `src/failure_injection/loop.py`
- ✅ Updated `src/offline_data/mind2web_loader.py` (state_after)
- ✅ Test results showing LOOP ≥5%

#### Acceptance Criteria:

- [ ] LOOP injector active and working
- [ ] LOOP failures ≥5% in test run
- [ ] Recovery strategies generated
- [ ] No memory issues with state_after

---

### **Phase 3: Full Dataset Generation** 📊

**Priority**: HIGH  
**Duration**: 2-3 days  
**Dependency**: Phase 1 (quality gate pass) + Phase 2 (LOOP complete)

#### Tasks:

1. **Pre-scaling validation**
   - Run quality gate on pilot
   - Confirm all gates pass
   - Document baseline metrics

2. **Generate 500-task dataset**
   - Run: `python scripts/test_downloaded_data.py --num-tasks 500`
   - Monitor: memory usage, processing time
   - Save: `output/dataset_500/`
   - Validate: run quality gate on output

3. **Generate 1,000-task dataset** (if 500 passes)
   - Run: `python scripts/test_downloaded_data.py --num-tasks 1000`
   - Use all 1,019 available trajectories
   - Save: `output/dataset_1000_full/`
   - Validate: run quality gate

4. **Batch processing** (if memory issues)
   - Process in 200-task batches
   - Merge outputs
   - Validate merged dataset

5. **Quality assurance**
   - Run automated validation
   - Manual spot checks (10-20 random trajectories)
   - Compare pilot vs full dataset distributions

#### Deliverables:

- ✅ `output/dataset_500/` (500 trajectories, ~3,500 steps)
- ✅ `output/dataset_1000_full/` (1,000 trajectories, ~7,000 steps)
- ✅ Quality reports for both datasets
- ✅ Distribution comparison charts

#### Acceptance Criteria:

- [ ] 500-task dataset generated and validated
- [ ] 1,000-task dataset generated (if resources allow)
- [ ] All quality gates pass on full dataset
- [ ] Failure/recovery distributions match pilot

---

### **Phase 4: Baseline Model Development** 🤖

**Priority**: CRITICAL (for Q1 publication)  
**Duration**: 3-4 days  
**Purpose**: Prove dataset is learnable and useful

#### Tasks:

**4.1. Baseline 1: Rule-Based Failure Detector**

```python
# Simple heuristics
def detect_failure_rule_based(step):
    """
    Detect failures using simple rules.
    """
    # TARGET_MISSING: Low SSIM on target bbox region
    if bbox_ssim < 0.7:
        return "TARGET_MISSING"

    # NO_STATE_CHANGE: SSIM = 1.0, pixel_diff = 0
    if ssim > 0.98 and pixel_diff < 0.01:
        return "NO_STATE_CHANGE"

    # MISCLICK: Action coords far from target
    if distance(action_coords, target_center) > 150:
        return "MISCLICK"

    # Timeout-based detection
    if execution_time > 5.0:
        return "TIMEOUT_FAILURE"

    return "SUCCESS"
```

**Tasks:**

- Implement rule-based detector
- Test on validation set
- Report precision/recall/F1
- Analyze failure modes

**4.2. Baseline 2: Vision Classifier**

```python
# Small CNN/ViT
Model: ResNet-18 or ViT-Tiny
Input: [state_before, state_after]
Output: 6 classes [SUCCESS, TARGET_MISSING, MISCLICK,
                   WRONG_OPERATION, NO_STATE_CHANGE, LOOP]

Training:
  - 70% train / 15% val / 15% test split
  - Cross-entropy loss
  - Adam optimizer
  - 20 epochs
  - Early stopping on validation accuracy
```

**Tasks:**

- Implement vision classifier (PyTorch/TensorFlow)
- Train on 500-task dataset
- Evaluate on held-out test set
- Report accuracy, confusion matrix
- Compare with rule-based baseline

**4.3. Evaluation & Analysis**

- Compare baseline 1 vs baseline 2
- Per-class performance
- Error analysis
- Visualize predictions
- Document results

#### Deliverables:

- ✅ `src/baselines/rule_based_detector.py`
- ✅ `src/baselines/vision_classifier.py`
- ✅ `scripts/train_baseline_classifier.py`
- ✅ `output/baselines/results.json`
- ✅ `output/baselines/confusion_matrix.png`
- ✅ `docs/BASELINE_RESULTS.md`

#### Acceptance Criteria:

- [ ] Rule-based baseline implemented and evaluated
- [ ] Vision classifier trained (accuracy >60%)
- [ ] Both baselines documented with metrics
- [ ] Results ready for Q1 paper

---

### **Phase 5: Data Splitting & Preparation** 📦

**Priority**: MEDIUM  
**Duration**: 1 day  
**Dependency**: Phase 3 (full dataset)

#### Tasks:

1. **Split dataset**
   - Train: 70% (~700 trajectories)
   - Validation: 15% (~150 trajectories)
   - Test: 15% (~150 trajectories)
   - Stratified by: domain, failure type

2. **Create standard splits**
   - `dataset/train.json`
   - `dataset/val.json`
   - `dataset/test.json`
   - Document split methodology

3. **Generate dataset statistics**
   - Steps per split
   - Failure distribution per split
   - Domain distribution
   - Website coverage

4. **Package dataset**
   - Create HuggingFace dataset card
   - Prepare upload scripts
   - Add license (CC BY 4.0 recommended)

#### Deliverables:

- ✅ Train/val/test splits
- ✅ Dataset statistics report
- ✅ HuggingFace dataset card

#### Acceptance Criteria:

- [ ] Splits are balanced across failure types
- [ ] No data leakage between splits
- [ ] Statistics documented

---

### **Phase 6: Documentation & Dataset Card** 📝

**Priority**: HIGH  
**Duration**: 2 days  
**Purpose**: Make dataset publication-ready

#### Tasks:

1. **Write comprehensive dataset card**
   - Overview and motivation
   - Data collection methodology
   - Failure taxonomy
   - Injection algorithms
   - Schema documentation
   - Intended use cases
   - Limitations and biases
   - License and citation

2. **Create usage examples**
   - Loading dataset
   - Training failure detector
   - Training recovery policy
   - Evaluation scripts

3. **Generate visualizations**
   - Failure type distribution
   - Per-injector success rates
   - Domain coverage
   - Example trajectories with screenshots

4. **Write README for GitHub**
   - Quick start guide
   - Installation
   - Usage examples
   - Citation

#### Deliverables:

- ✅ `docs/DATASET_CARD.md`
- ✅ `examples/train_failure_detector.py`
- ✅ `examples/train_recovery_policy.py`
- ✅ `README.md` (updated)

#### Acceptance Criteria:

- [ ] Dataset card follows HuggingFace template
- [ ] All code examples run successfully
- [ ] Documentation is clear and complete

---

### **Phase 7: Q1 Journal Paper Preparation** 📄

**Priority**: HIGH  
**Duration**: 5-7 days  
**Dependency**: All previous phases

#### Tasks:

1. **Draft paper structure**
   - Abstract
   - Introduction (motivation, contributions)
   - Related Work (web agents, failure recovery, datasets)
   - Methodology (data collection, augmentation, injection)
   - Experiments (baselines, results)
   - Discussion (findings, limitations)
   - Conclusion

2. **Prepare figures and tables**
   - Figure 1: System architecture
   - Figure 2: Failure taxonomy
   - Figure 3: Injection examples
   - Figure 4: Baseline results
   - Table 1: Dataset statistics
   - Table 2: Comparison with existing datasets

3. **Write experimental section**
   - Baseline results
   - Ablation studies
   - Error analysis
   - Discussion of findings

4. **Perform literature review**
   - Related datasets (WebShop, MiniWoB, Mind2Web)
   - Failure recovery methods
   - Web agent architectures
   - Cite 30-40 relevant papers

5. **Internal review**
   - Self-review for clarity
   - Check all claims have evidence
   - Verify all figures are referenced
   - Proofread

#### Deliverables:

- ✅ Draft paper (6-8 pages)
- ✅ All figures and tables
- ✅ Supplementary materials
- ✅ Reference list

#### Acceptance Criteria:

- [ ] Paper follows Q1 journal template
- [ ] All sections complete
- [ ] Baselines and experiments documented
- [ ] Ready for submission

---

## 📅 Timeline

| Phase                       | Duration | Dependencies | Start Date | Target End |
| --------------------------- | -------- | ------------ | ---------- | ---------- |
| **Phase 1: Quality Gate**   | 1-2 days | None         | Feb 21     | Feb 23     |
| **Phase 2: LOOP Injector**  | 1 day    | None         | Feb 21     | Feb 22     |
| **Phase 3: Full Dataset**   | 2-3 days | Phase 1, 2   | Feb 23     | Feb 26     |
| **Phase 4: Baselines**      | 3-4 days | Phase 3      | Feb 26     | Mar 2      |
| **Phase 5: Data Splitting** | 1 day    | Phase 3      | Feb 26     | Feb 27     |
| **Phase 6: Documentation**  | 2 days   | Phase 3, 4   | Mar 2      | Mar 4      |
| **Phase 7: Paper Writing**  | 5-7 days | All          | Mar 4      | Mar 11     |

**Total Duration**: ~18-20 days (~3 weeks)  
**Target Submission**: Mid-March 2026

---

## ⚠️ Risk Management

### Risk 1: Quality Gate Failure

**Probability**: Medium  
**Impact**: High  
**Mitigation**:

- Fix pilot issues before scaling
- Re-run with adjusted config if needed
- Document all adjustments

### Risk 2: Memory Issues at Scale

**Probability**: Medium  
**Impact**: Medium  
**Mitigation**:

- Batch processing (200 tasks at a time)
- Disable screenshot saving if needed
- Use streaming mode

### Risk 3: LOOP Injector Complexity

**Probability**: Low  
**Impact**: Medium  
**Mitigation**:

- Can proceed without LOOP (4 types sufficient)
- Mark as limitation in paper
- Future work item

### Risk 4: Baseline Performance Too Low

**Probability**: Low  
**Impact**: High  
**Mitigation**:

- Tune hyperparameters
- Try different architectures
- Add feature engineering
- If <50% accuracy, investigate data quality

### Risk 5: Timeline Slip

**Probability**: Medium  
**Impact**: Medium  
**Mitigation**:

- Focus on critical path (Phases 1-4, 7)
- Phase 6 can be done in parallel with Phase 7
- Request deadline extension if needed

---

## 🎯 Success Metrics

### Dataset Quality:

- ✅ Failure rate: 40-60%
- ✅ All 5 failure types present (≥5% each)
- ✅ Recovery strategies for all failures
- ✅ No missing data
- ✅ Schema compliant

### Model Performance:

- ✅ Rule-based baseline: F1 >50%
- ✅ Vision classifier: Accuracy >60%
- ✅ Better than random (16.7% for 6 classes)

### Publication Readiness:

- ✅ Dataset card complete
- ✅ Code and data public
- ✅ Paper drafted
- ✅ Baselines documented
- ✅ Reproducibility guaranteed

---

## 📞 Next Actions (Immediate)

1. **Today (Feb 21):**
   - Implement quality gate script
   - Start LOOP injector implementation

2. **Tomorrow (Feb 22):**
   - Complete LOOP injector
   - Run quality gate on pilot
   - Fix any issues

3. **Feb 23-26:**
   - Generate full dataset (500-1,000 tasks)
   - Validate quality

4. **Feb 26 - Mar 2:**
   - Implement and train baselines
   - Document results

5. **Mar 2-11:**
   - Write documentation
   - Draft paper
   - Prepare for submission

---

**Document Status**: Living document (update after each phase)  
**Last Updated**: February 21, 2026  
**Owner**: Thesis Project - Data Collection System
