# Task-04: Failure Labeling

**Phase:** 4  
**Priority:** 🔴 High  
**Status:** ⬜ Not Started  
**Estimated Duration:** 2 weeks  
**Assigned To:** [Your Name]  
**Start Date:** -  
**Completion Date:** -

---

## 1. Objective

Implement an automated failure detection and diagnosis system that categorizes execution failures into structured types, computes failure confidence scores, and prepares data for recovery strategy generation.

---

## 2. Deliverables

### 2.1 Failure Detection Engine

- [ ] Visual difference-based detection
- [ ] Loop detection via state hashing
- [ ] Browser exception capture
- [ ] Timeout signal handling

### 2.2 Failure Categorization

- [ ] PERCEPTION_ERROR
- [ ] ACTION_MISMATCH
- [ ] STATE_NO_CHANGE
- [ ] LOOP_DETECTED
- [ ] GOAL_MISALIGNMENT
- [ ] TOOL_FAILURE
- [ ] UI_VARIATION
- [ ] REASONING_ERROR
- [ ] NONE (success)

### 2.3 Diagnosis Logic

- [ ] Visual metric analysis
- [ ] Grounding mismatch detection
- [ ] Task objective heuristics
- [ ] Multi-signal aggregation

### 2.4 Confidence Scoring

- [ ] Failure confidence (0.0 - 1.0)
- [ ] Evidence scoring
- [ ] Uncertainty quantification

---

## 3. Technical Specifications

### 3.1 Failure Schema

```python
{
    "step_id": int,
    "execution_outcome": str,     # SUCCESS | FAILURE | UNCERTAIN
    "failure_type": str,          # One of 9 categories
    "failure_confidence": float,  # 0.0 - 1.0
    "failure_evidence": {
        "visual_diff": float,
        "state_unchanged": bool,
        "loop_detected": bool,
        "exception_raised": bool,
        "timeout_occurred": bool
    },
    "diagnosis_timestamp": str
}
```

### 3.2 FailureLabeler API

```python
class FailureLabeler:
    def detect_failure(self, step: Step, metrics: Metrics) -> bool
    def diagnose_failure(self, step: Step, context: Context) -> FailureLabel
    def compute_confidence(self, evidence: Dict) -> float
    def categorize(self, diagnosis: Dict) -> str
    def aggregate_signals(self, signals: List[Signal]) -> Diagnosis
```

---

## 4. Implementation Steps

### Step 1: Detection Logic (Days 1-3)

- [ ] Visual diff threshold detection
- [ ] Loop detection algorithm
- [ ] Exception capturing
- [ ] Timeout handling

### Step 2: Categorization Rules (Days 4-6)

- [ ] Rule-based classifier
- [ ] Decision tree implementation
- [ ] Multi-signal integration
- [ ] Edge case handling

### Step 3: Diagnosis Engine (Days 7-9)

- [ ] Evidence aggregation
- [ ] Confidence computation
- [ ] Uncertainty handling
- [ ] Validation on samples

### Step 4: Integration (Days 10-11)

- [ ] Integrate with metric computation
- [ ] Update JSONL schema
- [ ] Batch processing mode

### Step 5: Validation & Tuning (Days 12-14)

- [ ] Manual annotation of 100 samples
- [ ] Tune thresholds
- [ ] Validate accuracy
- [ ] Error analysis

---

## 5. Failure Type Definitions

### PERCEPTION_ERROR

- Agent cannot locate target element
- Visual grounding failure
- Detection: Element selector fails + no exception

### ACTION_MISMATCH

- Wrong action executed
- Element exists but action ineffective
- Detection: State changes but not as expected

### STATE_NO_CHANGE

- Action executed but no visible change
- Detection: visual_diff < 0.05

### LOOP_DETECTED

- Agent repeating same actions
- Detection: state_hash appears 3+ times

### GOAL_MISALIGNMENT

- Action doesn't advance task goal
- Detection: Heuristic based on task description

### TOOL_FAILURE

- Browser exception or crash
- Detection: Exception caught

### UI_VARIATION

- Page structure changed unexpectedly
- Detection: Major visual diff without action

### REASONING_ERROR

- Logical mistake in action sequence
- Detection: Context-based inference

### NONE

- Successful execution
- Detection: Normal progression

---

## 6. Dependencies

### External Dependencies

- None (uses internal metrics)

### Internal Dependencies

- Task-03: Metric Computation (for visual diff, state hash)
- Task-02: Browser Recorder (for action logs)

---

## 7. Success Criteria

✅ **Task complete when:**

1. Failure detection accuracy > 85%
2. All 9 failure types implemented
3. Confidence scores validated
4. Integration with existing pipeline
5. Manual validation on 100 samples
6. Documentation complete

---

## 8. Testing Checklist

- [ ] Test on 50 successful trajectories
- [ ] Test on 50 failed trajectories
- [ ] Validate each failure category
- [ ] Check confidence score distribution
- [ ] Edge case testing
- [ ] Performance benchmarks (<50ms per step)

---

## 9. Validation Protocol

1. **Manual Annotation**
   - Select 100 random steps
   - Human expert labels failure type
   - Compare with automated labels
2. **Accuracy Metrics**
   - Precision/Recall per category
   - Overall accuracy
   - Cohen's Kappa score

3. **Threshold Tuning**
   - Optimize F1 score
   - Balance false positives/negatives

---

## 10. Risk & Mitigation

| Risk                   | Mitigation                           |
| ---------------------- | ------------------------------------ |
| Low detection accuracy | Multi-signal fusion, manual review   |
| Ambiguous failures     | UNCERTAIN label, confidence scoring  |
| Category imbalance     | Weighted sampling, data augmentation |

---

## 11. Progress Log

### 2026-02-19

- Task file created
- Status: Not Started
- Blocked by: Task-03 completion

---

## 12. Notes

- Start with high-confidence cases (loops, exceptions)
- Use manual annotation for training initial rules
- Keep rules interpretable for debugging
- Plan for future ML-based classifier

---

**Last Updated:** February 19, 2026  
**Next Review:** March 19, 2026
