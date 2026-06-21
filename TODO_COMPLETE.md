# TODO List - Failure-Aware Dataset Completion

**Last Updated**: February 21, 2026  
**Status**: Ready to Execute  
**Target**: Q1 Journal Submission (Mid-March 2026)

---

## 🎯 CRITICAL PATH (Must Complete in Order)

### ⏰ IMMEDIATE (TODAY - Feb 21)

#### STEP 1: Fix LOOP Failure Injector

- [ ] **1.1** Implement `state_after` screenshot loading in `mind2web_loader.py`
  - [ ] Add `next_action_sample` parameter to `_parse_single_action_step()`
  - [ ] Load screenshot from next action's row index
  - [ ] Handle edge case (last action has no next)
  - [ ] Update `OfflineStep` to store `state_after`
- [ ] **1.2** Update trajectory parsing to pass next action
  - [ ] Modify `_parse_trajectory_from_actions()` loop
  - [ ] Get next action: `actions_sorted[step_idx + 1]`
  - [ ] Pass to parsing function
- [ ] **1.3** Complete LOOP injector logic in `loop.py`
  - [ ] Update `can_inject()` to check for `state_after`
  - [ ] Implement SSIM comparison in `inject()`
  - [ ] Detect natural loops (SSIM > 0.95)
  - [ ] Force loops by setting `state_after = state_before`
  - [ ] Check for repetition in history
  - [ ] Generate appropriate recovery strategies
- [ ] **1.4** Test LOOP injector
  - [ ] Run on 20 tasks: `python scripts/test_downloaded_data.py --num-tasks 20 --output-dir output/test_loop_fix --load-screenshots`
  - [ ] Verify LOOP ≥5% of failures
  - [ ] Check memory usage (<4GB for 20 tasks)
  - [ ] Verify recovery strategies generated

**Acceptance**: LOOP injector working, test shows ≥5% LOOP failures

---

### ⏰ TOMORROW (Feb 22)

#### STEP 2: Implement Quality Gate System

- [ ] **2.1** Create quality gate validation script
  - [ ] Create file: `scripts/validate_quality_gate.py`
  - [ ] Implement `QualityThresholds` dataclass
  - [ ] Implement `QualityGate` class
  - [ ] **Gate 1**: Check failure rate (40-60%)
  - [ ] **Gate 2**: Check LOOP presence (≥5%)
  - [ ] **Gate 3**: Check recovery strategies (>0%)
  - [ ] **Gate 4**: Check for missing screenshots/fields
  - [ ] **Gate 5**: Check all failure types present
  - [ ] Implement HTML report generation
- [ ] **2.2** Run quality gate on current pilot (will FAIL - expected)
  - [ ] Run: `python scripts/validate_quality_gate.py --summary output/pilot_100_final/summary.json --trajectories output/pilot_100_final/augmented_trajectories.json --output output/pilot_100_final/quality_report.html`
  - [ ] Confirm LOOP gate fails (0% LOOP)
  - [ ] Document other issues if any
- [ ] **2.3** Regenerate pilot with fixed LOOP
  - [ ] Run: `python scripts/test_downloaded_data.py --num-tasks 100 --output-dir output/pilot_100_with_loop --load-screenshots`
  - [ ] Should take ~2-3 minutes
  - [ ] Check output files created
- [ ] **2.4** Validate regenerated pilot
  - [ ] Run quality gate again
  - [ ] **MUST PASS all 5 gates**
  - [ ] Review HTML report
  - [ ] Document any issues and fix

**Acceptance**: Quality gate script working, regenerated pilot PASSES all gates

---

### ⏰ SUNDAY (Feb 23-26)

#### STEP 3: Scale to Full Dataset (500-1,000 Tasks)

- [ ] **3.1** Pre-flight checklist
  - [ ] Confirm quality gate PASSED on pilot
  - [ ] Check disk space (need ~10 GB free)
  - [ ] Check RAM available (8GB+)
  - [ ] Backup current outputs
- [ ] **3.2** Generate 500-task dataset
  - [ ] Run: `python scripts/test_downloaded_data.py --num-tasks 500 --output-dir output/dataset_500 --load-screenshots`
  - [ ] Monitor during run (~5-10 minutes)
  - [ ] Expected: ~3,500 steps, ~2-3GB RAM
  - [ ] Check for errors in output
- [ ] **3.3** Validate 500-task dataset
  - [ ] Run quality gate
  - [ ] **MUST PASS before continuing**
  - [ ] Compare distributions to pilot (should be ±10%)
  - [ ] Document any drift
- [ ] **3.4** Generate 1,000-task dataset
  - [ ] Run: `python scripts/test_downloaded_data.py --num-tasks 1000 --output-dir output/dataset_1000_full --load-screenshots`
  - [ ] Monitor (~10-15 minutes)
  - [ ] Expected: ~7,000 steps, ~4-5GB RAM
- [ ] **3.5** Validate 1,000-task dataset
  - [ ] Run quality gate
  - [ ] **MUST PASS**
  - [ ] Generate comparison report (pilot vs 500 vs 1000)
- [ ] **3.6** Create dataset split script
  - [ ] Create `scripts/split_dataset.py`
  - [ ] Split: 70% train / 15% val / 15% test
  - [ ] Verify no trajectory leakage between splits
  - [ ] Save to `dataset/train.json`, `dataset/val.json`, `dataset/test.json`

**Acceptance**: 1,000-task dataset generated and validated, split into train/val/test

---

### ⏰ MONDAY-TUESDAY (Feb 26-27)

#### STEP 4: Comprehensive Quality Assurance

- [ ] **4.1** Create comprehensive QA script
  - [ ] Create `scripts/comprehensive_qa.py`
  - [ ] Implement `check_statistics()` - validate distributions
  - [ ] Implement `check_edge_cases()` - first/last steps, single-step trajectories
  - [ ] Implement `check_schema_compliance()` - all fields present and correct types
  - [ ] Implement `check_data_integrity()` - no duplicates, sequential numbering, valid coords
  - [ ] Generate detailed report
- [ ] **4.2** Run automated QA
  - [ ] Run on full dataset
  - [ ] Document all issues found
  - [ ] Fix critical issues
  - [ ] Re-run until clean
- [ ] **4.3** Manual inspection
  - [ ] Create checklist: `docs/MANUAL_QA_CHECKLIST.md`
  - [ ] Randomly sample 10 trajectories
  - [ ] Sample 2 trajectories per failure type (10 more)
  - [ ] For each, check:
    - [ ] Screenshot quality (no artifacts)
    - [ ] Failure injection realistic
    - [ ] Recovery strategy makes sense
    - [ ] Action sequence logical
    - [ ] No obvious bugs
  - [ ] Fill checklist: `docs/manual_qa_checklist_filled.md`
- [ ] **4.4** Domain coverage analysis
  - [ ] Create `scripts/analyze_coverage.py`
  - [ ] Count unique websites
  - [ ] Analyze domain distribution
  - [ ] Check action type diversity
  - [ ] Check trajectory length distribution
  - [ ] Generate visualizations
- [ ] **4.5** Generate final QA report
  - [ ] Combine automated + manual results
  - [ ] Generate HTML report
  - [ ] Save to `output/dataset_1000_full/qa_comprehensive_report.html`

**Acceptance**: All automated checks pass, manual inspection confirms quality

---

### ⏰ WED-SAT (Feb 27 - Mar 2)

#### STEP 5: Build Baseline Models (CRITICAL FOR Q1)

- [ ] **5.1** Implement Rule-Based Detector
  - [ ] Create `src/baselines/rule_based_detector.py`
  - [ ] Implement `RuleBasedDetector` class
  - [ ] Rule 1: NO_STATE_CHANGE (SSIM ≈ 1.0)
  - [ ] Rule 2: TARGET_MISSING (low sharpness on target region)
  - [ ] Rule 3: MISCLICK (action coords far from target)
  - [ ] Rule 4: WRONG_OPERATION (skip for baseline)
  - [ ] Rule 5: LOOP (skip for baseline)
  - [ ] Default: SUCCESS
- [ ] **5.2** Evaluate rule-based detector
  - [ ] Load test split
  - [ ] Run predictions
  - [ ] Calculate accuracy, precision, recall, F1
  - [ ] Generate classification report
  - [ ] Generate confusion matrix
  - [ ] Save results: `output/baselines/rule_based_results.json`
  - [ ] **Target**: Accuracy >50%
- [ ] **5.3** Implement Vision Classifier
  - [ ] Create `src/baselines/vision_classifier.py`
  - [ ] Implement `FailureDataset` class
    - [ ] Load before/after screenshots
    - [ ] Concatenate (6 channels)
    - [ ] Transform to 224x224
  - [ ] Implement `FailureClassifier` (ResNet-18 based)
    - [ ] Modify first conv for 6 channels
    - [ ] 6-class output
  - [ ] Implement training loop (20 epochs)
- [ ] **5.4** Train vision classifier
  - [ ] Install PyTorch: `pip install torch torchvision`
  - [ ] Run training: `python src/baselines/vision_classifier.py --train`
  - [ ] Monitor validation accuracy
  - [ ] Save best model: `output/baselines/vision_classifier_best.pth`
  - [ ] Expected training time: ~20 minutes (GPU), ~2 hours (CPU)
- [ ] **5.5** Evaluate vision classifier
  - [ ] Run on test set
  - [ ] Calculate metrics
  - [ ] Generate classification report
  - [ ] Generate confusion matrix
  - [ ] Compare to rule-based
  - [ ] Save results: `output/baselines/vision_classifier_results.json`
  - [ ] **Target**: Accuracy >60%
- [ ] **5.6** Compare baselines
  - [ ] Create `scripts/compare_baselines.py`
  - [ ] Compare accuracy: random (16.7%), rule-based, vision
  - [ ] Generate comparison table
  - [ ] Create visualization (bar chart)
  - [ ] Save report: `output/baselines/comparison_report.html`
- [ ] **5.7** Document baseline results
  - [ ] Create `docs/BASELINE_RESULTS.md`
  - [ ] Document methodology
  - [ ] Include result tables
  - [ ] Include confusion matrices
  - [ ] Write conclusion (dataset is learnable)

**Acceptance**: Both baselines working, rule-based >50%, vision >60%, both >> random

---

### ⏰ SUN-MON (Mar 2-4)

#### STEP 6: Documentation and Dataset Card

- [ ] **6.1** Write dataset card
  - [ ] Create `docs/DATASET_CARD.md`
  - [ ] Section 1: Overview (what, why, statistics)
  - [ ] Section 2: Dataset Description (source, methodology, scale)
  - [ ] Section 3: Schema Documentation (all fields documented)
  - [ ] Section 4: Failure Taxonomy (5 types with examples)
  - [ ] Section 5: Injection Methodology (algorithms explained)
  - [ ] Section 6: Intended Use Cases
  - [ ] Section 7: Limitations
  - [ ] Section 8: License and Citation
- [ ] **6.2** Create usage examples
  - [ ] Create `examples/load_and_explore.py`
    - [ ] Load dataset
    - [ ] Print statistics
    - [ ] Explore first trajectory
  - [ ] Create `examples/visualize_failures.py`
    - [ ] Load augmented steps
    - [ ] Draw bboxes and action coords
    - [ ] Show failure type labels
    - [ ] Save visualizations
  - [ ] Test both examples work
- [ ] **6.3** Update main README
  - [ ] Add dataset statistics table
  - [ ] Add quick start section
  - [ ] Add links to documentation
  - [ ] Add citation
  - [ ] Add license
  - [ ] Add examples
- [ ] **6.4** Generate visual assets
  - [ ] Create `scripts/generate_charts.py`
  - [ ] Generate failure distribution pie chart
  - [ ] Generate domain coverage bar chart
  - [ ] Generate injector success rates
  - [ ] Generate trajectory length histogram
  - [ ] Save to `docs/assets/`
- [ ] **6.5** Create supplementary materials
  - [ ] Zip code and scripts
  - [ ] Create requirements.txt
  - [ ] Write INSTALLATION.md
  - [ ] Test installation on clean environment

**Acceptance**: Complete documentation ready, examples working, README polished

---

### ⏰ TUE-MON (Mar 4-11)

#### STEP 7: Write Q1 Journal Paper

- [ ] **7.1** Paper structure and outline
  - [ ] Choose target journal (Q1 in AI/ML)
  - [ ] Download LaTeX template
  - [ ] Create paper outline with sections
  - [ ] Estimate page count per section
- [ ] **7.2** Write introduction and related work (Day 1-2)
  - [ ] Draft introduction
    - [ ] Motivation (web agents need robustness)
    - [ ] Problem (no failure datasets)
    - [ ] Solution (systematic augmentation)
    - [ ] Contributions (4-5 bullet points)
  - [ ] Write related work
    - [ ] Web agent datasets (Mind2Web, WebShop, etc.)
    - [ ] Failure recovery (robotics, dialog systems)
    - [ ] Data augmentation (CV, NLP)
    - [ ] Robustness in AI
- [ ] **7.3** Write methodology (Day 2-3)
  - [ ] Describe source data
  - [ ] Explain failure taxonomy
  - [ ] Detail each injection algorithm
  - [ ] Explain recovery generation
  - [ ] Describe quality assurance
- [ ] **7.4** Write experiments section (Day 3-4)
  - [ ] Dataset description
  - [ ] Experimental setup
  - [ ] Baseline 1: Rule-based
    - [ ] Methodology
    - [ ] Results
  - [ ] Baseline 2: Vision classifier
    - [ ] Architecture
    - [ ] Training details
    - [ ] Results
  - [ ] Comparison and analysis
  - [ ] Error analysis
- [ ] **7.5** Create all figures (Day 5)
  - [ ] Figure 1: System architecture diagram
  - [ ] Figure 2: Failure taxonomy with examples
  - [ ] Figure 3: Dataset statistics
  - [ ] Figure 4: Baseline performance comparison
  - [ ] Figure 5: Confusion matrices
  - [ ] All figures high quality, camera-ready
- [ ] **7.6** Create all tables (Day 5)
  - [ ] Table 1: Dataset comparison (ours vs others)
  - [ ] Table 2: Failure distribution
  - [ ] Table 3: Baseline results
  - [ ] Format for journal style
- [ ] **7.7** Write discussion and conclusion (Day 6)
  - [ ] Discuss key findings
  - [ ] Interpret baseline results
  - [ ] Acknowledge limitations
  - [ ] Suggest future work
  - [ ] Write conclusion (contributions, impact)
- [ ] **7.8** Write abstract (Day 6)
  - [ ] Summarize problem, solution, results
  - [ ] 200 words max
  - [ ] Revise for clarity
- [ ] **7.9** Polish and proofread (Day 7)
  - [ ] Check all references formatted correctly
  - [ ] Proofread entire paper
  - [ ] Check figure/table references
  - [ ] Verify citations
  - [ ] Run spell check
  - [ ] Internal review
- [ ] **7.10** Prepare submission package
  - [ ] Main paper PDF
  - [ ] Supplementary materials
  - [ ] Dataset link or upload
  - [ ] Code repository link
  - [ ] Cover letter

**Acceptance**: Complete paper ready for Q1 journal submission

---

## 📊 Progress Tracking

### Overall Status:

| Phase                     | Tasks  | Completed | In Progress | Not Started | Status         |
| ------------------------- | ------ | --------- | ----------- | ----------- | -------------- |
| **STEP 1: LOOP Fix**      | 4      | 0         | 0           | 4           | 🔴 Not Started |
| **STEP 2: Quality Gate**  | 4      | 0         | 0           | 4           | 🔴 Not Started |
| **STEP 3: Scale Dataset** | 6      | 0         | 0           | 6           | 🔴 Not Started |
| **STEP 4: QA**            | 5      | 0         | 0           | 5           | 🔴 Not Started |
| **STEP 5: Baselines**     | 7      | 0         | 0           | 7           | 🔴 Not Started |
| **STEP 6: Documentation** | 5      | 0         | 0           | 5           | 🔴 Not Started |
| **STEP 7: Paper**         | 10     | 0         | 0           | 10          | 🔴 Not Started |
| **TOTAL**                 | **41** | **0**     | **0**       | **41**      |                |

---

## 🚨 Critical Dependencies

```
CANNOT START STEP 2 until STEP 1 is COMPLETE
CANNOT START STEP 3 until Quality Gate PASSES in STEP 2
CANNOT START STEP 5 until STEP 3 is COMPLETE (need full dataset)
CANNOT SUBMIT PAPER (STEP 7) without BASELINES (STEP 5)
```

---

## ⚠️ Blockers and Risks

### Active Blockers:

1. **LOOP injector not working** → Blocks everything
   - **Action**: Start immediately (TODAY)
   - **Owner**: You
   - **Deadline**: Tomorrow (Feb 22)

### Potential Risks:

| Risk                        | Impact | Probability | Mitigation                                 |
| --------------------------- | ------ | ----------- | ------------------------------------------ |
| Quality gate fails on pilot | High   | Medium      | Fix LOOP first, thorough testing           |
| Memory issues at 1k scale   | Medium | Low         | Batch processing, monitor RAM              |
| Baseline accuracy too low   | High   | Low         | Try multiple architectures                 |
| Paper rejected              | High   | Medium      | Get internal review, follow best practices |
| Timeline slip               | Medium | Medium      | Focus on critical path, cut non-essentials |

---

## 📅 Key Milestones

- [x] **Feb 20**: Pilot dataset complete (86 trajectories, 59.4% failure rate)
- [ ] **Feb 22**: LOOP fixed, quality gate implemented, pilot validated
- [ ] **Feb 26**: Full 1,000-task dataset generated and validated
- [ ] **Feb 27**: Comprehensive QA complete
- [ ] **Mar 2**: Both baselines trained and evaluated
- [ ] **Mar 4**: All documentation complete
- [ ] **Mar 11**: Paper draft complete
- [ ] **Mar 15**: Paper submitted to Q1 journal

---

## 🎯 Definition of Done

### LOOP Fix (Step 1):

- ✅ `state_after` loading implemented
- ✅ LOOP injector `can_inject()` returns True for valid steps
- ✅ Test shows LOOP ≥5% of failures
- ✅ Recovery strategies generated
- ✅ No memory issues

### Quality Gate (Step 2):

- ✅ Script implements all 5 gates
- ✅ Regenerated pilot PASSES all gates
- ✅ HTML report generated
- ✅ Ready to scale

### Full Dataset (Step 3):

- ✅ 1,000 tasks generated
- ✅ Quality gate PASSES
- ✅ Split into train/val/test
- ✅ Distributions consistent with pilot

### QA (Step 4):

- ✅ Automated checks pass
- ✅ Manual inspection complete
- ✅ Coverage analysis done
- ✅ No critical bugs

### Baselines (Step 5):

- ✅ Rule-based: >50% accuracy
- ✅ Vision classifier: >60% accuracy
- ✅ Both >> random (16.7%)
- ✅ Results documented

### Documentation (Step 6):

- ✅ Dataset card complete
- ✅ Examples working
- ✅ README polished
- ✅ Visual assets created

### Paper (Step 7):

- ✅ Draft complete (6-8 pages)
- ✅ All figures and tables
- ✅ Abstract written
- ✅ Proofread and reviewed
- ✅ Ready for submission

---

## 📝 Daily Checklist Template

### Start of Day:

- [ ] Review yesterday's progress
- [ ] Check which tasks are blocked
- [ ] Prioritize today's tasks
- [ ] Set clear goal for the day

### End of Day:

- [ ] Update this TODO list
- [ ] Document any issues found
- [ ] Commit all code changes
- [ ] Plan tomorrow's focus

---

## 📞 Quick Reference

### Key Commands:

```bash
# Test LOOP fix
python scripts/test_downloaded_data.py --num-tasks 20 --output-dir output/test_loop --load-screenshots

# Run quality gate
python scripts/validate_quality_gate.py --summary OUTPUT/summary.json --trajectories OUTPUT/augmented_trajectories.json --output OUTPUT/quality_report.html

# Generate full dataset
python scripts/test_downloaded_data.py --num-tasks 1000 --output-dir output/dataset_1000_full --load-screenshots

# Train baselines
python src/baselines/rule_based_detector.py --evaluate
python src/baselines/vision_classifier.py --train
```

### Key Files:

- Loader: `src/offline_data/mind2web_loader.py`
- LOOP: `src/failure_injection/loop.py`
- Engine: `src/failure_injection/injection_engine.py`
- Test: `scripts/test_downloaded_data.py`
- Quality: `scripts/validate_quality_gate.py` (to create)

---

**Last Updated**: February 21, 2026, 10:00 PM  
**Next Update**: After completing STEP 1 (LOOP fix)  
**Total Tasks Remaining**: 41

---

## 🎯 START HERE (RIGHT NOW):

### Immediate Action - STEP 1.1:

Open `src/offline_data/mind2web_loader.py` and start implementing `state_after` loading.

**File to edit**: Line ~400-500 in `_parse_single_action_step()`

**Change needed**: Add parameter `next_action_sample: Optional[Dict] = None`

**Next**: Load screenshot from `next_action_sample['_row_index']`

**GO! 🚀**
