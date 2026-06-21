# Task-06: Reflection Annotation

**Phase:** 6  
**Priority:** 🟢 Low  
**Status:** ⬜ Not Started  
**Estimated Duration:** 1 week  
**Assigned To:** [Your Name]  
**Start Date:** -  
**Completion Date:** -

---

## 1. Objective

Add introspective annotation layers that capture agent confidence, reasoning explanations, and memory update signals to support learning-based resilience research.

---

## 2. Deliverables

### 2.1 Confidence Scoring

- [ ] agent_confidence_before (pre-action)
- [ ] agent_confidence_after (post-action)
- [ ] Confidence estimation logic

### 2.2 Reflection Text Generation

- [ ] reflection_text field
- [ ] Natural language explanation
- [ ] Success/failure reasoning

### 2.3 Memory Update Signals

- [ ] memory_update_flag
- [ ] memory_type classification
- [ ] Experience indexing

### 2.4 Introspection Utilities

- [ ] Confidence calibration
- [ ] Reflection templates
- [ ] Signal aggregation

---

## 3. Technical Specifications

### 3.1 Reflection Schema

```python
{
    "step_id": int,
    "agent_confidence_before": float,  # 0.0 - 1.0
    "agent_confidence_after": float,   # 0.0 - 1.0
    "reflection_text": str,
    "memory_update_flag": bool,
    "memory_type": str,               # SUCCESS | FAILURE | RECOVERY | INSIGHT
    "confidence_calibration": float,  # Delta from expected
    "introspection_metadata": {
        "reasoning_type": str,
        "uncertainty_source": str,
        "learning_signal": str
    }
}
```

### 3.2 ReflectionAnnotator API

```python
class ReflectionAnnotator:
    def estimate_confidence(self, step: Step) -> float
    def generate_reflection(self, step: Step, outcome: Outcome) -> str
    def should_update_memory(self, step: Step) -> bool
    def classify_memory_type(self, step: Step) -> str
    def calibrate_confidence(self, expected: float, actual: float) -> float
```

---

## 4. Implementation Steps

### Step 1: Confidence Estimation (Days 1-2)

- [ ] Heuristic-based confidence scoring
- [ ] Feature extraction (visual, temporal)
- [ ] Calibration logic

### Step 2: Reflection Generation (Days 3-4)

- [ ] Template-based generation
- [ ] Success/failure explanations
- [ ] Context-aware reasoning

### Step 3: Memory Signals (Days 4-5)

- [ ] Memory update criteria
- [ ] Type classification
- [ ] Experience indexing

### Step 4: Integration (Days 6-7)

- [ ] Add to JSONL pipeline
- [ ] Validate on sample data
- [ ] Performance optimization

---

## 5. Confidence Estimation Logic

```python
def estimate_confidence(step: Step) -> float:
    """
    Factors:
    - Element visibility/clarity
    - Action success history
    - Page complexity
    - Previous failure rate
    - Time since last success
    """
    base_confidence = 0.8

    # Adjust based on element detection
    if element_not_found:
        base_confidence -= 0.3

    # Adjust based on history
    if recent_failures > 2:
        base_confidence -= 0.2

    # Adjust based on complexity
    if page_complexity_high:
        base_confidence -= 0.1

    return max(0.0, min(1.0, base_confidence))
```

---

## 6. Reflection Templates

### Success Template

```
"Successfully [ACTION] on [TARGET]. State changed as expected with high confidence (visual_diff={score})."
```

### Failure Template

```
"Failed to [ACTION] on [TARGET]. Diagnosed as [FAILURE_TYPE]. No significant state change detected (visual_diff={score}). Attempting [RECOVERY_STRATEGY]."
```

### Uncertainty Template

```
"Uncertain about action outcome. Visual change detected but unclear if goal was achieved. Confidence: {confidence}."
```

---

## 7. Memory Update Criteria

**Update memory when:**

- Novel failure type encountered
- Recovery strategy succeeded/failed
- Significant state transition
- High uncertainty resolved
- Loop pattern detected

**Memory Types:**

- SUCCESS: Effective action pattern
- FAILURE: Known error pattern
- RECOVERY: Working recovery strategy
- INSIGHT: New learning signal

---

## 8. Dependencies

### External Dependencies

- None (optional: simple NLG library)

### Internal Dependencies

- Task-04: Failure Labeling (for failure info)
- Task-05: Recovery Generation (for recovery info)

---

## 9. Success Criteria

✅ **Task complete when:**

1. Confidence scores generated for all steps
2. Reflection texts generated for key events
3. Memory signals properly flagged
4. Integration with JSONL pipeline
5. Manual validation on 50 samples
6. Documentation complete

---

## 10. Testing Checklist

- [ ] Generate confidence for 100 steps
- [ ] Validate confidence calibration
- [ ] Review 50 reflection texts
- [ ] Check memory flag accuracy
- [ ] Integration test with full pipeline
- [ ] Performance benchmarks (<10ms per step)

---

## 11. Confidence Calibration

Track confidence accuracy over time:

```python
calibration_error = |predicted_success_rate - actual_success_rate|
```

Adjust confidence thresholds if calibration_error > 0.15

---

## 12. Risk & Mitigation

| Risk                        | Mitigation                          |
| --------------------------- | ----------------------------------- |
| Generic reflections         | Add more contextual features        |
| Poor confidence calibration | Tune with validation set            |
| Excessive memory flags      | Stricter criteria, threshold tuning |

---

## 13. Example Output

```json
{
  "step_id": 42,
  "agent_confidence_before": 0.85,
  "agent_confidence_after": 0.4,
  "reflection_text": "Attempted to click 'Add to Cart' button but no state change detected. Likely a PERCEPTION_ERROR as element may not have been correctly identified. Attempting ALTERNATIVE_TARGET recovery.",
  "memory_update_flag": true,
  "memory_type": "FAILURE",
  "introspection_metadata": {
    "reasoning_type": "diagnosis",
    "uncertainty_source": "element_detection",
    "learning_signal": "improve_selector_strategy"
  }
}
```

---

## 14. Progress Log

### 2026-02-19

- Task file created
- Status: Not Started
- Blocked by: Task-05 completion

---

## 15. Notes

- Keep reflections concise but informative
- Confidence should correlate with success rate
- Memory signals support future RL/learning
- Consider multi-language support in future

---

**Last Updated:** February 19, 2026  
**Next Review:** April 2, 2026
