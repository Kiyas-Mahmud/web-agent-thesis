# Phase 5 Implementation TODO List
## Offline Failure Injection Approach

---

## 🔥 URGENT: Stop Current Collection

- [ ] **STOP-01:** Kill running pilot collection process
  - Stop the 50-task collection currently running
  - Reason: 100% failure rate indicates broken approach
  
- [ ] **STOP-02:** Archive current collected data
  - Move `dataset/collected/` to `dataset/archived_live_replay/`
  - Keep for reference, but don't use for training

---

## 📋 Phase 5.1: Offline Data Infrastructure (Week 1-3)

### Week 1: Data Loader & Validation

#### Priority 1: Setup Multimodal Mind2Web Dataset

- [ ] **DATA-01:** Create offline data loader module
  - File: `src/offline_data/mind2web_loader.py`
  - Class: `MultimodalMind2WebLoader`
  - Methods:
    - `load_trajectories()` - Load task trajectories
    - `load_screenshots()` - Load associated screenshots
    - `validate_data()` - Check data integrity
  
- [ ] **DATA-02:** Download Multimodal Mind2Web dataset
  - Source: `osunlp/Multimodal-Mind2Web` from HuggingFace
  - Save to: `dataset/mind2web_offline/`
  - Components needed:
    - Task definitions
    - Action annotations
    - Screenshots (state_before, state_after)
    - Metadata
  
- [ ] **DATA-03:** Create offline dataset schema
  - File: `src/offline_data/offline_schema.py`
  - Classes:
    - `OfflineTrajectory` - Container for trajectory + screenshots
    - `OfflineStep` - Single step with images
    - `AugmentedStep` - Step with injected failure
  
- [ ] **DATA-04:** Build data validation suite
  - Check: All screenshots exist
  - Check: Annotations match screenshots
  - Check: No missing steps
  - Check: Image dimensions consistent
  - File: `src/offline_data/validate_dataset.py`

#### Priority 2: Preprocessing Pipeline

- [ ] **PREP-01:** Create image preprocessing module
  - File: `src/offline_data/image_preprocessor.py`
  - Functions:
    - `resize_image()` - Standardize dimensions
    - `mask_bbox()` - For TARGET_MISSING injection
    - `add_noise()` - For NO_STATE_CHANGE injection
    - `compute_visual_diff()` - For validation
  
- [ ] **PREP-02:** Create annotation processor
  - File: `src/offline_data/annotation_processor.py`
  - Functions:
    - `parse_action()` - Extract action details
    - `extract_target_bbox()` - Get element bounding box
    - `find_alternative_targets()` - For recovery generation

---

### Week 2: Failure Injection Engine

#### Priority 1: Core Injection Framework

- [ ] **INJ-01:** Create failure injection base class
  - File: `src/failure_injection/injection_engine.py`
  - Class: `FailureInjector`
  - Methods:
    - `inject_failure(step, failure_type)` - Main injection
    - `validate_injection(step)` - Check validity
    - `get_ground_truth_labels(step)` - Auto-labeling

- [ ] **INJ-02:** Implement TARGET_MISSING injection
  - File: `src/failure_injection/target_missing.py`
  - Class: `TargetMissingInjector`
  - Methods:
    - `inject(step)` - Remove target from candidates / mask image
    - `label()` - Return failure_type='perception_error', subtype='ELEMENT_MISSING'
  - Test: Verify target truly invisible in output

- [ ] **INJ-03:** Implement MISCLICK injection
  - File: `src/failure_injection/misclick.py`
  - Class: `MisclickInjector`
  - Methods:
    - `inject(step)` - Shift coordinates randomly
    - `compute_offset()` - Determine shift amount
    - `label()` - Return failure_type='action_mismatch', subtype='WRONG_COORDINATES'
  - Test: Verify clicked coordinates outside target bbox

- [ ] **INJ-04:** Implement WRONG_OPERATION injection
  - File: `src/failure_injection/wrong_operation.py`
  - Class: `WrongOperationInjector`
  - Methods:
    - `inject(step)` - Swap action types
    - `get_incompatible_action()` - Choose wrong operation
    - `label()` - Return failure_type='reasoning_error', subtype='WRONG_ACTION_TYPE'
  - Test: Verify operation doesn't match expected

- [ ] **INJ-05:** Implement NO_STATE_CHANGE injection
  - File: `src/failure_injection/no_state_change.py`
  - Class: `NoStateChangeInjector`
  - Methods:
    - `inject(step)` - Set state_after = state_before
    - `compute_metrics()` - Ensure pixel_diff=0, ssim=1.0
    - `label()` - Return failure_type='state_no_change', subtype='NO_VISUAL_RESPONSE'
  - Test: Verify metrics confirm no change

- [ ] **INJ-06:** Implement LOOP injection
  - File: `src/failure_injection/loop.py`
  - Class: `LoopInjector`
  - Methods:
    - `inject(trajectory, step_idx)` - Create loop sequence
    - `repeat_state()` - Use previous state
    - `label()` - Return failure_type='loop_detected', subtype='STATE_LOOP'
  - Test: Verify loop detector would fire

#### Priority 2: Injection Configuration

- [ ] **INJ-07:** Create injection configuration system
  - File: `src/failure_injection/injection_config.py`
  - Class: `InjectionConfig`
  - Parameters:
    ```python
    {
        'overall_injection_rate': 0.60,  # 60% of steps get failures
        'failure_distribution': {
            'TARGET_MISSING': 0.27,      # 27% of failures
            'MISCLICK': 0.23,
            'WRONG_OPERATION': 0.20,
            'NO_STATE_CHANGE': 0.17,
            'LOOP': 0.13
        },
        'recovery_enabled': True,
        'recovery_success_rate': 0.60    # 60% of recoveries succeed
    }
    ```

- [ ] **INJ-08:** Build injection pipeline orchestrator
  - File: `src/failure_injection/pipeline.py`
  - Class: `InjectionPipeline`
  - Methods:
    - `process_trajectory(trajectory, config)` - Main entry
    - `select_steps_for_injection(trajectory)` - Which steps
    - `inject_and_label(step, failure_type)` - Apply injection
    - `validate_distribution(results)` - Check balance
  
- [ ] **INJ-09:** Add injection validation tests
  - File: `tests/test_failure_injection.py`
  - Tests:
    - Verify each injection type works
    - Check label consistency
    - Validate distribution matches config
    - Ensure no data corruption

---

### Week 3: Recovery Synthesis Engine

#### Priority 1: Recovery Generation

- [ ] **REC-01:** Create recovery generator base
  - File: `src/recovery_synthesis/recovery_generator.py`
  - Class: `RecoveryGenerator`
  - Methods:
    - `generate_recovery(failed_step, failure_type)`
    - `evaluate_recovery_success(recovery_step, gold_trajectory)`
  
- [ ] **REC-02:** Implement recovery mappings
  - File: `src/recovery_synthesis/recovery_mappings.py`
  - Define recovery strategies per failure type:
    ```python
    RECOVERY_MAPPING = {
        'TARGET_MISSING': {
            'methods': ['ALTERNATIVE_TARGET', 'SCROLL_AND_RETRY'],
            'steps_needed': 1,
            'success_rate': 0.65
        },
        'MISCLICK': {
            'methods': ['BACKTRACK', 'CLICK_CORRECT_TARGET'],
            'steps_needed': 2,
            'success_rate': 0.55
        },
        # ... etc for all types
    }
    ```

- [ ] **REC-03:** Build recovery action generator
  - File: `src/recovery_synthesis/action_generator.py`
  - Functions:
    - `generate_backtrack_action(failed_step)`
    - `generate_retry_action(failed_step)`
    - `generate_alternative_target(failed_step, candidates)`
    - `generate_replan_action(failed_step, task_context)`
  
- [ ] **REC-04:** Implement recovery success evaluator
  - File: `src/recovery_synthesis/success_evaluator.py`
  - Class: `RecoverySuccessEvaluator`
  - Methods:
    - `check_trajectory_alignment(after_recovery, gold_step)`
    - `check_state_progress(recovery_step)`
    - `assign_recovery_label(recovery_sequence)`

#### Priority 2: Recovery Labeling

- [ ] **REC-05:** Add recovery fields to augmented step schema
  - Update: `src/offline_data/offline_schema.py`
  - Add fields:
    ```python
    recovery_attempted: bool
    recovery_method: str  # RETRY, BACKTRACK, ALTERNATIVE_TARGET, etc.
    recovery_step_span: List[int]  # [failure_step_id, last_recovery_step_id]
    recovery_success: bool
    recovery_duration_ms: float
    recovery_steps_needed: int
    ```

- [ ] **REC-06:** Create recovery validation suite
  - File: `tests/test_recovery_synthesis.py`
  - Tests:
    - Verify recovery_success is never null
    - Check recovery rate > 0%
    - Validate recovery method matches failure type
    - Ensure recovery steps are valid actions

---

## 📊 Phase 5.2: Dataset Generation (Week 4-6)

### Week 4: Pilot Generation

#### Priority 1: Pilot Collection

- [ ] **PILOT-01:** Configure pilot generation
  - Create config: `configs/pilot_generation.yaml`
  - Parameters:
    ```yaml
    dataset: mind2web
    num_tasks: 100
    injection_config:
      overall_rate: 0.60
      recovery_enabled: true
    output_dir: dataset/pilot_offline/
    ```

- [ ] **PILOT-02:** Create generation runner script
  - File: `scripts/generate_offline_dataset.py`
  - Functions:
    - Load offline data
    - Apply failure injection
    - Generate recovery steps
    - Save augmented trajectories
  
- [ ] **PILOT-03:** Run pilot generation
  - Generate 100 trajectories
  - Expected output:
    - ~1,000-1,500 steps total
    - ~400-600 clean success steps
    - ~300-400 failure steps (recoverable)
    - ~150-200 failure steps (non-recoverable)

#### Priority 2: Validation

- [ ] **PILOT-04:** Validate pilot distribution
  - File: `scripts/validate_pilot.py`
  - Checks:
    - Success rate: 40-50%
    - Failure rate: 30-40%
    - Recovery rate: 55-65%
    - All failure types present
    - Recovery success > 0%
  
- [ ] **PILOT-05:** Manual inspection
  - Sample 20 trajectories randomly
  - Check:
    - Injections make sense
    - Recovery actions are logical
    - Labels are correct
    - No data corruption
  - Document findings: `docs/pilot_inspection_report.md`
  
- [ ] **PILOT-06:** Run updated quality gates
  - Script: `_quality_gates.py` (modify for offline data)
  - Expected results:
    - Gate A: ✅ Pass (0% error pages)
    - Gate B: ✅ Pass (>95% success consistency)
    - Gate C: ✅ Pass (balanced distribution)
    - Gate D: ✅ Pass (>80% recovery tracking)
    - Gate E: ✅ Pass (30-60% failure rate)

---

### Week 5: Full Scale Collection

#### Priority 1: Scale Up

- [ ] **FULL-01:** Configure full collection
  - Create config: `configs/full_generation.yaml`
  - Parameters:
    ```yaml
    dataset: mind2web
    num_tasks: 1000
    steps_per_task: 8-15
    total_expected_steps: 10000-15000
    injection_config: {same as pilot}
    output_dir: dataset/offline_augmented/
    ```

- [ ] **FULL-02:** Run full generation in batches
  - Batch 1: 250 tasks
  - Batch 2: 250 tasks
  - Batch 3: 250 tasks
  - Batch 4: 250 tasks
  - Monitor each batch before continuing
  
- [ ] **FULL-03:** Merge batches
  - Combine all batches
  - Remove duplicates
  - Verify total count
  
- [ ] **FULL-04:** Generate training splits
  - Train: 70% (~7,000 steps)
  - Val: 15% (~1,500 steps)
  - Test: 15% (~1,500 steps)
  - Save splits: `dataset/offline_augmented/splits/`

---

### Week 6: Quality Assurance

#### Priority 1: Dataset Validation

- [ ] **QA-01:** Run comprehensive quality checks
  - File: `scripts/comprehensive_qa.py`
  - Checks:
    - All images load correctly
    - No missing labels
    - Distribution matches targets
    - No outlier metrics
    - Consistent schema
  
- [ ] **QA-02:** Compute dataset statistics
  - File: `scripts/compute_statistics.py`
  - Generate report:
    - Total trajectories, steps
    - Failure type breakdown
    - Recovery success rates per type
    - Average steps per trajectory
    - Visual metrics distribution
  - Save: `dataset/offline_augmented/statistics.json`

- [ ] **QA-03:** Create dataset documentation
  - File: `dataset/offline_augmented/README.md`
  - Include:
    - Dataset description
    - Collection methodology
    - Distribution statistics
    - Usage examples
    - Citation information

#### Priority 2: Final Verification

- [ ] **QA-04:** Cross-validate with external checker
  - Load random sample
  - Manually verify 50 steps
  - Check labels match visual evidence
  - Document any issues
  
- [ ] **QA-05:** Run final quality gates
  - All gates must pass
  - Document results
  - Sign off for Phase 6 training
  
- [ ] **QA-06:** Create dataset release
  - Version: v1.0
  - Tag in git
  - Create distribution package
  - Upload to storage (if needed)

---

## 🔧 Infrastructure Updates

### Code Refactoring

- [ ] **REFACTOR-01:** Update success/failure detection logic
  - File: `src/failure_labeling/decision_tree.py`
  - Remove chrome-error page handling (not needed for offline)
  - Update classification to work with offline metrics
  
- [ ] **REFACTOR-02:** Modify monitor for offline metrics
  - File: `src/monitoring/dashboard.py`
  - Remove live replay metrics
  - Add offline injection tracking
  - Separate success/partial/failure clearly

- [ ] **REFACTOR-03:** Update collect_runner for offline mode
  - File: `src/collection_runner/collect_runner.py`
  - Add offline generation mode
  - Skip browser initialization for offline
  - Use offline data loader instead of browser replay

### Testing

- [ ] **TEST-01:** Unit tests for injection engine
  - File: `tests/unit/test_injection_engine.py`
  - Test each injector independently
  - Verify labels are correct
  
- [ ] **TEST-02:** Integration tests for pipeline
  - File: `tests/integration/test_offline_pipeline.py`
  - Test full trajectory processing
  - Verify end-to-end flow

- [ ] **TEST-03:** Validation tests for quality gates
  - File: `tests/validation/test_quality_gates.py`
  - Test gate calculations
  - Verify thresholds

---

## 📚 Documentation

- [ ] **DOC-01:** Update main README
  - Add section on offline generation approach
  - Explain why switch from live replay
  - Link to strategy analysis
  
- [ ] **DOC-02:** Create offline generation tutorial
  - File: `docs/offline_generation_tutorial.md`
  - Step-by-step guide
  - Code examples
  - Troubleshooting

- [ ] **DOC-03:** Document failure injection API
  - File: `docs/failure_injection_api.md`
  - Class references
  - Usage examples
  - Configuration options

- [ ] **DOC-04:** Create recovery synthesis guide
  - File: `docs/recovery_synthesis_guide.md`
  - Recovery strategies explained
  - Success criteria
  - Labeling guidelines

---

## ⏱️ Timeline Summary

| Week | Phase | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | Data Infrastructure | Offline loader + validation | 🔴 Not Started |
| 2 | Failure Injection | 5 injector types implemented | 🔴 Not Started |
| 3 | Recovery Synthesis | Recovery generator working | 🔴 Not Started |
| 4 | Pilot Generation | 100 tasks validated | 🔴 Not Started |
| 5 | Full Collection | 1,000 tasks generated | 🔴 Not Started |
| 6 | Quality Assurance | Dataset ready for Phase 6 | 🔴 Not Started |

---

## 🎯 Success Criteria

### Phase 5.1 Complete When:
- [x] All 5 injector types working
- [x] Recovery generator produces valid steps
- [x] Pilot passes all quality gates
- [x] Distribution matches targets

### Phase 5.2 Complete When:
- [x] 5,000-15,000 training steps generated
- [x] Failure rate: 30-60%
- [x] Recovery rate: 55-65%
- [x] All quality gates pass
- [x] Dataset documentation complete

### Ready for Phase 6 When:
- [x] Dataset validated
- [x] Train/val/test splits created
- [x] Baseline metrics computed
- [x] Data loaders tested

---

## 📊 Key Metrics to Track

During implementation, monitor:

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Success Rate | 40-50% | TBD | 🔵 Pending |
| Failure Rate | 30-40% | TBD | 🔵 Pending |
| Recovery Rate | 55-65% | TBD | 🔵 Pending |
| TARGET_MISSING | ~27% of failures | TBD | 🔵 Pending |
| MISCLICK | ~23% of failures | TBD | 🔵 Pending |
| WRONG_OPERATION | ~20% of failures | TBD | 🔵 Pending |
| NO_STATE_CHANGE | ~17% of failures | TBD | 🔵 Pending |
| LOOP | ~13% of failures | TBD | 🔵 Pending |
| Recovery Success | 55-65% | TBD | 🔵 Pending |

---

## 🚨 Critical Path Items

These must be done first (blocking):

1. **STOP-01:** Stop current collection
2. **DATA-01:** Create offline data loader
3. **DATA-02:** Download Multimodal Mind2Web
4. **INJ-01:** Build injection framework
5. **REC-01:** Build recovery generator

All other tasks depend on these.

---

## ✅ Weekly Progress Checklist

### Week 1 Done When:
- [ ] Multimodal Mind2Web downloaded
- [ ] Offline loader working
- [ ] Data validation passing
- [ ] First 10 trajectories loaded successfully

### Week 2 Done When:
- [ ] All 5 injectors implemented
- [ ] Injection config system working
- [ ] Tests passing
- [ ] Can inject failures into loaded data

### Week 3 Done When:
- [ ] Recovery generator working
- [ ] Recovery labels assigned correctly
- [ ] Success evaluator functional
- [ ] End-to-end pipeline tested

### Week 4 Done When:
- [ ] 100-task pilot generated
- [ ] Distribution validated
- [ ] Quality gates pass
- [ ] Manual inspection complete

### Week 5 Done When:
- [ ] 1,000 tasks generated
- [ ] Batches merged
- [ ] Splits created
- [ ] Statistics computed

### Week 6 Done When:
- [ ] All QA checks pass
- [ ] Documentation complete
- [ ] Dataset released
- [ ] Ready for Phase 6

---

## 📞 Support & Questions

If blockers arise:
1. Check `PHASE5_STRATEGY_ANALYSIS.md` for rationale
2. Review injection/recovery examples
3. Validate data format
4. Check quality gates

**Goal:** Research-quality dataset with controlled, balanced failures and measurable recoveries for training failure-aware agents.
