# TODO List - Failure-Aware Dataset Project

**Last Updated**: February 21, 2026  
**Status**: Pilot Complete → Scaling Phase

---

## 🚨 CRITICAL PATH (Must Complete for Q1)

### Phase 1: Quality Gate Implementation

- [ ] Create `scripts/validate_quality_gate.py`
  - [ ] Implement failure rate check (40-60%)
  - [ ] Implement LOOP percentage check (≥5%)
  - [ ] Implement recovery rate check (>0%)
  - [ ] Implement missing data check (=0)
  - [ ] Implement schema validation
- [ ] Define quality metrics dataclass
- [ ] Run quality gate on pilot dataset
- [ ] Generate quality report HTML
- [ ] Fix any issues found
- [ ] Document pass/fail criteria

**Deadline**: Feb 23  
**Blocking**: Phase 3 (scaling)

---

### Phase 2: LOOP Injector Completion

- [ ] Implement `state_after` loading in mind2web_loader.py
  - [ ] Modify `_parse_single_action_step()`
  - [ ] Load next screenshot for state_after
  - [ ] Handle last step edge case
  - [ ] Test memory usage
- [ ] Complete LOOP detection logic in loop.py
  - [ ] Implement SSIM comparison (>0.95)
  - [ ] Detect repeated action patterns
  - [ ] Add history context requirement (2+ steps)
- [ ] Implement LOOP injection
  - [ ] Repeat 2-3 actions
  - [ ] Keep states identical
  - [ ] Generate recovery strategy
- [ ] Test LOOP injector on 20 tasks
- [ ] Verify LOOP ≥5% in output

**Deadline**: Feb 22  
**Blocking**: Phase 1 (quality gate LOOP check)

---

### Phase 3: Full Dataset Generation

- [ ] Pre-scaling validation
  - [ ] Run quality gate on pilot
  - [ ] Confirm all gates pass
  - [ ] Document baseline metrics
- [ ] Generate 500-task dataset
  - [ ] Run script: `--num-tasks 500`
  - [ ] Monitor memory and time
  - [ ] Save to `output/dataset_500/`
  - [ ] Run quality gate validation
- [ ] If 500 passes, generate 1,000-task dataset
  - [ ] Run script: `--num-tasks 1000`
  - [ ] Save to `output/dataset_1000_full/`
  - [ ] Run quality gate validation
- [ ] Quality assurance
  - [ ] Automated validation
  - [ ] Manual spot checks (10-20 trajectories)
  - [ ] Distribution comparison

**Deadline**: Feb 26  
**Blocking**: Phase 4, 5

---

### Phase 4: Baseline Models (CRITICAL for Q1)

- [ ] **Baseline 1: Rule-Based Detector**
  - [ ] Create `src/baselines/rule_based_detector.py`
  - [ ] Implement heuristic rules
    - [ ] TARGET_MISSING: bbox SSIM < 0.7
    - [ ] NO_STATE_CHANGE: SSIM > 0.98
    - [ ] MISCLICK: distance > 150px
    - [ ] WRONG_OPERATION: action mismatch
  - [ ] Test on validation set
  - [ ] Calculate precision/recall/F1
  - [ ] Document results

- [ ] **Baseline 2: Vision Classifier**
  - [ ] Create `src/baselines/vision_classifier.py`
  - [ ] Choose model (ResNet-18 or ViT-Tiny)
  - [ ] Implement data loader
  - [ ] Implement training script
  - [ ] Split data (70/15/15)
  - [ ] Train for 20 epochs
  - [ ] Evaluate on test set
  - [ ] Generate confusion matrix
  - [ ] Document results

- [ ] **Comparison & Analysis**
  - [ ] Compare baseline 1 vs 2
  - [ ] Per-class performance analysis
  - [ ] Error analysis
  - [ ] Create visualizations
  - [ ] Write `docs/BASELINE_RESULTS.md`

**Deadline**: Mar 2  
**Blocking**: Phase 7 (paper experiments section)

---

## 📋 SECONDARY TASKS (Important but not blocking)

### Phase 5: Data Splitting

- [ ] Implement stratified split function
- [ ] Split into train/val/test (70/15/15)
- [ ] Verify no data leakage
- [ ] Check distribution balance
- [ ] Save splits to `dataset/`
- [ ] Generate statistics per split
- [ ] Document split methodology

**Deadline**: Feb 27

---

### Phase 6: Documentation

- [ ] **Dataset Card** (`docs/DATASET_CARD.md`)
  - [ ] Overview and motivation
  - [ ] Data collection methodology
  - [ ] Failure taxonomy description
  - [ ] Injection algorithms
  - [ ] Schema documentation
  - [ ] Intended use cases
  - [ ] Limitations and biases
  - [ ] License and citation

- [ ] **Usage Examples**
  - [ ] Create `examples/train_failure_detector.py`
  - [ ] Create `examples/train_recovery_policy.py`
  - [ ] Create `examples/load_dataset.py`
  - [ ] Test all examples

- [ ] **Visualizations**
  - [ ] Failure distribution chart
  - [ ] Injector success rates chart
  - [ ] Domain coverage chart
  - [ ] Example trajectory gallery

- [ ] **README Update**
  - [ ] Add dataset card link
  - [ ] Add usage examples
  - [ ] Add installation instructions
  - [ ] Add citation

**Deadline**: Mar 4

---

### Phase 7: Q1 Paper Writing

- [ ] **Structure**
  - [ ] Write abstract (150-200 words)
  - [ ] Write introduction (1.5 pages)
  - [ ] Write related work (1.5 pages)
  - [ ] Write methodology (2 pages)
  - [ ] Write experiments (1.5 pages)
  - [ ] Write discussion (1 page)
  - [ ] Write conclusion (0.5 pages)

- [ ] **Figures & Tables**
  - [ ] Figure 1: System architecture diagram
  - [ ] Figure 2: Failure taxonomy
  - [ ] Figure 3: Injection examples (before/after)
  - [ ] Figure 4: Baseline results (bar chart)
  - [ ] Table 1: Dataset statistics
  - [ ] Table 2: Comparison with existing datasets
  - [ ] Table 3: Baseline performance metrics

- [ ] **Experiments Section**
  - [ ] Describe baseline 1 setup and results
  - [ ] Describe baseline 2 setup and results
  - [ ] Ablation study (if time permits)
  - [ ] Error analysis
  - [ ] Discussion of findings

- [ ] **Literature Review**
  - [ ] Cite related datasets (Mind2Web, WebShop, MiniWoB)
  - [ ] Cite failure recovery methods
  - [ ] Cite web agent papers
  - [ ] Total: 30-40 references

- [ ] **Review & Polish**
  - [ ] Self-review for clarity
  - [ ] Verify all claims have evidence
  - [ ] Check all figures referenced
  - [ ] Proofread for grammar/typos
  - [ ] Check formatting matches journal template

**Deadline**: Mar 11

---

## ⏰ IMMEDIATE NEXT ACTIONS (Today/Tomorrow)

### Today - Feb 21 (Friday)

- [ ] **Morning**: Implement quality gate script skeleton
- [ ] **Afternoon**: Start LOOP state_after loading
- [ ] **Evening**: Test quality gate on pilot

### Tomorrow - Feb 22 (Saturday)

- [ ] **Morning**: Complete LOOP injector
- [ ] **Afternoon**: Test LOOP on 20 tasks
- [ ] **Evening**: Run full quality gate, document results

### Next Week - Feb 23-26 (Mon-Thu)

- [ ] **Mon**: Fix any quality gate issues
- [ ] **Tue**: Generate 500-task dataset
- [ ] **Wed**: Validate 500-task, start 1,000-task
- [ ] **Thu**: Complete 1,000-task, final validation

---

## 📊 Progress Tracking

### Completed ✅

- [x] Phase 5 system architecture design
- [x] Mind2Web loader implementation
- [x] JSON parsing (operation, bbox)
- [x] Screenshot loading
- [x] 4 failure injectors (TARGET_MISSING, MISCLICK, WRONG_OPERATION, NO_STATE_CHANGE)
- [x] Injection pipeline
- [x] 100-task pilot generation
- [x] System architecture documentation

### In Progress 🔄

- [ ] Quality gate implementation
- [ ] LOOP injector completion

### Not Started ⏸️

- [ ] Full dataset generation (500-1,000)
- [ ] Baseline models
- [ ] Data splitting
- [ ] Dataset card
- [ ] Paper writing

---

## 🎯 Key Metrics to Track

| Metric            | Pilot | Target      | Current  |
| ----------------- | ----- | ----------- | -------- |
| Trajectories      | 86    | 500-1,000   | 86       |
| Total Steps       | 547   | 3,500-7,000 | 547      |
| Failure Rate      | 59.4% | 40-60%      | 59.4% ✅ |
| LOOP %            | 0%    | ≥5%         | 0% ❌    |
| Recovery Rate     | TBD   | >0%         | TBD      |
| Missing Data      | 0     | 0           | 0 ✅     |
| Baseline Accuracy | -     | >60%        | -        |

---

## 📞 Questions/Blockers

### Current Blockers:

1. None (pilot complete)

### Questions to Resolve:

1. Target dataset size: 500 or 1,000 tasks?
   - **Decision**: Start with 500, scale to 1,000 if resources allow

2. Vision classifier architecture: ResNet-18 or ViT?
   - **Decision**: Start with ResNet-18 (simpler, faster)

3. Paper target journal?
   - **Decision**: TBD (Q1 ranked journal in AI/ML)

---

## 🔔 Reminders

- **Quality gate MUST pass** before scaling to 500/1,000
- **Baselines are essential** for Q1 publication
- **Document everything** as you go
- **Test frequently** to catch issues early
- **Keep backups** of all generated datasets

---

**Next Update**: After Phase 1 & 2 completion (Feb 23)
