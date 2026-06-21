# Task-03: Metric Computation

**Phase:** 3  
**Priority:** 🟡 Medium  
**Status:** ⬜ Not Started  
**Estimated Duration:** 1 week  
**Assigned To:** [Your Name]  
**Start Date:** -  
**Completion Date:** -

---

## 1. Objective

Develop a metric computation system that analyzes before/after screenshots to compute visual difference scores, state hashes, and other quantitative metrics for detecting state changes and failures.

---

## 2. Deliverables

### 2.1 Visual Difference Computation

- [ ] Pixel-level difference score
- [ ] Structural similarity (SSIM)
- [ ] Perceptual hash difference
- [ ] Region-of-interest detection

### 2.2 State Hashing

- [ ] Screenshot hash generation
- [ ] State fingerprinting
- [ ] Loop detection logic

### 2.3 Statistical Metrics

- [ ] Action execution time
- [ ] State stability duration
- [ ] Page load metrics

### 2.4 Metric Storage

- [ ] Append metrics to JSONL
- [ ] Summary statistics
- [ ] Visualization utilities

---

## 3. Technical Specifications

### 3.1 Metrics Schema

```python
{
    "step_id": int,
    "visual_diff_score": float,      # 0.0 - 1.0
    "ssim_score": float,             # Structural similarity
    "perceptual_hash_diff": int,     # Hamming distance
    "state_hash": str,               # SHA-256 digest
    "execution_time_ms": float,
    "stability_wait_ms": float,
    "page_load_time_ms": float
}
```

### 3.2 MetricComputer API

```python
class MetricComputer:
    def compute_visual_diff(self, img1: Image, img2: Image) -> float
    def compute_ssim(self, img1: Image, img2: Image) -> float
    def compute_state_hash(self, img: Image) -> str
    def compute_perceptual_hash(self, img: Image) -> str
    def detect_loop(self, state_history: List[str]) -> bool
    def aggregate_metrics(self, steps: List[Step]) -> Dict
```

---

## 4. Implementation Steps

### Step 1: Visual Diff Implementation (Days 1-2)

- [ ] Pixel-level comparison
- [ ] SSIM implementation
- [ ] Test with sample images
- [ ] Optimize performance

### Step 2: State Hashing (Days 2-3)

- [ ] Perceptual hashing
- [ ] SHA-256 state fingerprinting
- [ ] Loop detection algorithm

### Step 3: Execution Metrics (Day 3)

- [ ] Timing instrumentation
- [ ] Performance tracking
- [ ] Metric aggregation

### Step 4: Integration (Days 4-5)

- [ ] Integrate with BrowserRecorder
- [ ] Update JSONL output
- [ ] Batch processing support

### Step 5: Visualization Tools (Days 6-7)

- [ ] Metric plotting utilities
- [ ] Summary report generation
- [ ] Dashboard prototypes

---

## 5. Dependencies

### External Dependencies

- OpenCV (cv2) or Pillow
- scikit-image (for SSIM)
- imagehash (for perceptual hashing)
- numpy

### Internal Dependencies

- Task-02: Browser Recorder (for screenshot input)

---

## 6. Success Criteria

✅ **Task complete when:**

1. Visual diff scores computed accurately
2. State hashes enable loop detection
3. Metrics integrated into JSONL output
4. Performance acceptable (<100ms per comparison)
5. Unit tests pass with >90% coverage
6. Visualization tools functional

---

## 7. Testing Checklist

- [ ] Compute metrics for 100 step pairs
- [ ] Validate visual diff thresholds
- [ ] Test loop detection accuracy
- [ ] Performance benchmarks
- [ ] Edge case handling (identical images, blank screens)
- [ ] Integration test with BrowserRecorder

---

## 8. Metric Thresholds

| Metric            | No Change | Minor Change | Major Change |
| ----------------- | --------- | ------------ | ------------ |
| visual_diff_score | < 0.05    | 0.05 - 0.30  | > 0.30       |
| ssim_score        | > 0.95    | 0.70 - 0.95  | < 0.70       |
| perceptual_hash   | < 5       | 5 - 15       | > 15         |

---

## 9. Risk & Mitigation

| Risk             | Mitigation                                |
| ---------------- | ----------------------------------------- |
| Slow computation | Optimize algorithms, use GPU if available |
| False positives  | Tune thresholds with validation set       |
| Hash collisions  | Use multiple hash methods                 |

---

## 10. Progress Log

### 2026-02-19

- Task file created
- Status: Not Started
- Blocked by: Task-02 completion

---

## 11. Notes

- Focus on fast, reliable metrics first
- Consider GPU acceleration for large batches
- Keep threshold values configurable
- Document all metric formulas

---

**Last Updated:** February 19, 2026  
**Next Review:** March 12, 2026
