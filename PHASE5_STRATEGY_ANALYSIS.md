# Phase 5 Strategy Analysis: Offline Failure Injection Approach

## Executive Summary

**Current Status:** Collection system shows 100% failure rate with 0% recovery - indicating fundamental architectural issues, not realistic web interaction data.

**Root Cause:** Live browser replay on real websites causes systematic failures (bot protection, chrome-error pages, timeouts) that cannot be used for training failure-aware agents.

**Solution:** Switch from live replay to **offline augmentation** using Multimodal Mind2Web screenshots with systematic failure injection.

---

## 🔴 Current Approach - Why It Fails

### Problems Identified

1. **Chrome Error Pages (9.1%)**
   - Browser lands on `chrome-error://chromewebdata/`
   - Caused by: DNS errors, network timeouts, HTTP/2 issues, bot protection
   - **Current bug:** Marked as SUCCESS despite being error page
   - **Impact:** Invalid training data

2. **100% Failure Rate**
   - NOT realistic for agent training
   - Caused by:
     - Page loading failures
     - Bot protection (united.com, discogs, etc.)
     - Invalid success detection logic
     - Selector timeouts on dynamic sites
   - **Impact:** Model learns "everything fails" - useless for recovery training

3. **0% Recovery Execution**
   - Recovery strategies assigned but never attempted
   - No measurement of recovery success
   - **Impact:** Phase 7 (Recovery Policy Training) impossible

4. **Invalid Success Criteria**

   ```python
   # CURRENT (WRONG):
   if no_exception:
       execution_outcome = "SUCCESS"  # Even if page is chrome-error://

   # REQUIRED:
   if page_loaded AND state_changed AND no_error_page:
       execution_outcome = "SUCCESS"
   ```

5. **DOM-based vs Vision-based Mismatch**
   - Using DOM selectors: `#bookCarTab`, `.CalendarDay`
   - But project goal is **vision-based** grounding
   - Without trained grounding model → 100% selector timeouts

### Why Live Replay Fails for Phase 5

| Issue              | Impact              | Frequency    |
| ------------------ | ------------------- | ------------ |
| Bot protection     | Task blocked        | 30-40%       |
| CAPTCHA            | Cannot proceed      | 10-20%       |
| Dynamic UI changes | Selectors invalid   | 20-30%       |
| Timeouts           | No page load        | 15-25%       |
| chrome-error pages | Invalid state       | 9%           |
| **NET RESULT**     | **~100% "failure"** | **Unusable** |

---

## ✅ Required Approach: Offline Failure Injection

### Core Concept

**Do NOT replay on live websites during Phase 5.**

Instead:

1. Load existing **Multimodal Mind2Web** trajectories (with screenshots)
2. Inject synthetic failures **offline** (no browser needed)
3. Generate synthetic recovery steps
4. Create balanced, controllable dataset

### Why This Works

| Aspect          | Live Replay       | Offline Injection                      |
| --------------- | ----------------- | -------------------------------------- |
| Bot protection  | ❌ Blocks 40%     | ✅ None                                |
| Reproducibility | ❌ Sites change   | ✅ Perfect                             |
| Failure control | ❌ Random         | ✅ Systematic                          |
| Recovery labels | ❌ Cannot measure | ✅ Synthetic truth                     |
| Dataset balance | ❌ 100% fail      | ✅ 40% success, 30% fail, 30% recovery |

---

## 📊 Dataset Strategy

### Primary Dataset: Mind2Web + Multimodal Mind2Web

**Use:**

- **Mind2Web:** Task definitions, action annotations, trajectories
- **Multimodal Mind2Web:** Screenshots (state_before, state_after)

**Source:**

- HuggingFace: `osunlp/Multimodal-Mind2Web`
- Contains: ~2,000 tasks, ~50,000 steps with screenshots

**Why:**

- Real websites, real tasks
- Human-annotated trajectories
- Pre-captured screenshots (no bot issues)
- Replayable for offline augmentation
- Publishable credibility

### Secondary Dataset: MiniWoB++

**Use for:**

- Early debugging
- Controlled experiments
- Recovery policy prototyping

### Evaluation Dataset: VisualWebArena

**Use ONLY for:**

- Final evaluation (Phase 8)
- NOT for training

---

## 🎯 Failure Injection Mechanisms (5 Types)

### 1. TARGET_MISSING (Perception Error)

**Inject by:**

```python
# Remove target bbox from candidates
annotations_modified = [a for a in annotations if a['id'] != target_id]

# OR mask target region in image
state_before_masked = mask_bbox(state_before, target_bbox)
```

**Expected Label:**

- `failure_type`: `perception_error`
- `failure_subtype`: `ELEMENT_MISSING`
- `root_cause`: Target element invisible or occluded

**Recovery:**

- `recovery_strategy`: `SCROLL_AND_RETRY` or `ALTERNATIVE_TARGET`

---

### 2. MISCLICK (Action Mismatch)

**Inject by:**

```python
# Shift click coordinates away from target
original_coords = (x, y)
misclick_coords = (x + random.randint(50, 200), y + random.randint(50, 200))
action_modified = action.copy()
action_modified['coordinates'] = misclick_coords
```

**Expected Label:**

- `failure_type`: `action_mismatch`
- `failure_subtype`: `WRONG_COORDINATES`
- `root_cause`: Clicked wrong element

**Recovery:**

- `recovery_strategy`: `BACKTRACK` then `CLICK_CORRECT_TARGET`

---

### 3. WRONG_OPERATION (Reasoning Error)

**Inject by:**

```python
# Swap action type
operation_swaps = {
    'CLICK': 'TYPE',
    'TYPE': 'CLICK',
    'SELECT': 'CLICK',
    'SCROLL': 'CLICK'
}
action_modified = action.copy()
action_modified['action_type'] = operation_swaps[action['action_type']]
```

**Expected Label:**

- `failure_type`: `reasoning_error`
- `failure_subtype`: `WRONG_ACTION_TYPE`
- `root_cause`: Incorrect operation for task context

**Recovery:**

- `recovery_strategy`: `REPLAN` then correct action

---

### 4. NO_STATE_CHANGE (Ineffective Action)

**Inject by:**

```python
# Set state_after = state_before (or tiny noise)
state_after_modified = state_before.copy()
# OR add imperceptible noise
state_after_modified = add_noise(state_before, epsilon=0.001)

# Metrics
pixel_diff = 0.0
ssim = 1.0
url_after = url_before
```

**Expected Label:**

- `failure_type`: `state_no_change`
- `failure_subtype`: `NO_VISUAL_RESPONSE`
- `root_cause`: Action had no effect

**Recovery:**

- `recovery_strategy`: `RETRY` or `ALTERNATIVE_ACTION`

---

### 5. LOOP (Repetitive Behavior)

**Inject by:**

```python
# Create mini-loop: step t after-image = step t-2 after-image
trajectory_modified = trajectory.copy()
trajectory_modified[t]['state_after'] = trajectory_modified[t-2]['state_after']
trajectory_modified[t]['url_after'] = trajectory_modified[t-2]['url_after']

# Repeat 3 times for loop detection
for i in range(3):
    trajectory_modified[t+i]['state_after'] = same_state
```

**Expected Label:**

- `failure_type`: `loop_detected`
- `failure_subtype`: `STATE_LOOP` or `URL_LOOP`
- `root_cause`: Agent stuck repeating same actions

**Recovery:**

- `recovery_strategy`: `BACKTRACK_TO_LAST_GOOD_STATE`

---

## 🔄 Recovery Synthesis

### Recovery Step Generation

For each injected failure, **generate synthetic recovery step(s)**:

```python
def generate_recovery_step(failed_step, failure_type):
    recovery_mapping = {
        'TARGET_MISSING': {
            'method': 'ALTERNATIVE_TARGET',
            'action': find_alternative_target(failed_step),
            'steps_needed': 1
        },
        'MISCLICK': {
            'method': 'BACKTRACK',
            'action': [navigate_back(), click_correct_target()],
            'steps_needed': 2
        },
        'WRONG_OPERATION': {
            'method': 'REPLAN',
            'action': correct_action_type(failed_step),
            'steps_needed': 1
        },
        'NO_STATE_CHANGE': {
            'method': 'RETRY',
            'action': failed_step.action,  # Same action, retry
            'steps_needed': 1
        },
        'LOOP': {
            'method': 'BACKTRACK',
            'action': restore_to_step(failed_step - 3),
            'steps_needed': 1
        }
    }

    return recovery_mapping[failure_type]
```

### Recovery Success Criteria

**Recovered = True if:**

1. After recovery, agent returns to **gold trajectory alignment**
   - `gold_step_i` or `gold_step_i+1` matched
2. OR state changes meaningfully:
   - `pixel_diff > threshold` (e.g., 0.01)
   - `ssim < threshold` (e.g., 0.95)
3. OR URL progresses correctly

**Recovered = False if:**

- Recovery attempted but still stuck
- New failure introduced
- Task terminated

---

## 📈 Target Dataset Distribution

### Ideal Balanced Dataset

For 10,000 steps:

| Category                               | Percentage | Count | Purpose            |
| -------------------------------------- | ---------- | ----- | ------------------ |
| **Clean Success**                      | 40%        | 4,000 | Baseline behavior  |
| **Injected Failure (Recoverable)**     | 30%        | 3,000 | Recovery training  |
| **Injected Failure (Non-recoverable)** | 15%        | 1,500 | Diagnosis training |
| **Natural Ambiguity**                  | 15%        | 1,500 | Robustness         |

### Per-Failure-Type Distribution

Target for 3,000 recoverable failures:

| Failure Type    | Count | Recovery Rate |
| --------------- | ----- | ------------- |
| TARGET_MISSING  | 800   | 60-70%        |
| MISCLICK        | 700   | 50-60%        |
| WRONG_OPERATION | 600   | 55-65%        |
| NO_STATE_CHANGE | 500   | 40-50%        |
| LOOP            | 400   | 70-80%        |

**Overall Recovery Rate Target:** 55-65%

---

## 🔧 Implementation Plan

### Phase 5.1: Offline Data Infrastructure

**Week 1: Data Loader & Preprocessor**

1. Load Multimodal Mind2Web
   - Download screenshots
   - Parse trajectories
   - Validate data integrity

2. Create offline dataset class
   ```python
   class OfflineMind2WebDataset:
       def __init__(self, data_dir):
           self.trajectories = load_trajectories()
           self.screenshots = load_screenshots()

       def __getitem__(self, idx):
           return {
               'task_id': ...,
               'steps': [...],
               'screenshots': {...}
           }
   ```

**Week 2: Failure Injection Engine**

1. Implement 5 injection types
2. Configurable injection probabilities
3. Validation checks

**Week 3: Recovery Synthesis**

1. Recovery step generator
2. Success criteria evaluator
3. Recovery label assignment

---

### Phase 5.2: Dataset Generation

**Week 4: Pilot Collection**

1. Generate 100 trajectories
2. Validate distribution:
   - 40% success, 30% fail, 30% recovery
   - All failure types represented
   - Recovery rate > 0%
3. Manual inspection of 20 samples

**Week 5: Full Collection**

1. Generate 500-1,000 tasks
2. ~8-15 steps per task
3. Total: 5,000-15,000 training samples

**Week 6: Validation & Quality Check**

1. Run quality gates
2. Check label consistency
3. Verify recovery balance

---

### Phase 6-9: Training & Evaluation

**Phase 6 (Weeks 7-8):** Failure Detection Model

- Input: state_before, state_after, action, metrics
- Output: failure_type, confidence
- Model: Vision encoder + classifier

**Phase 7 (Weeks 9-10):** Recovery Policy

- Input: failed_step, failure_type, state
- Output: recovery_action
- Model: Behavior cloning from synthetic labels

**Phase 8 (Week 11):** VisualWebArena Evaluation

- Deploy trained models
- Evaluate on live tasks
- Measure recovery success rate

**Phase 9 (Week 12):** Demo & Paper Writing

---

## ✅ Quality Gates (Updated)

### Gate A: Error Page Rate < 2%

**OLD:** 9.1% chrome-error pages
**NEW:** 0% (offline approach eliminates this)
**Status:** ✅ Will Pass

### Gate B: Success Consistency > 95%

**OLD:** 60% (invalid SUCCESS labels)
**NEW:** Define success properly in offline setting
**Status:** ✅ Will Pass

### Gate C: Balanced Failure Distribution

**OLD:** 69.7% perception_error (overused)
**NEW:** Controlled injection ensures balance
**Status:** ✅ Will Pass

### Gate D: Recovery Execution Rate > 80%

**OLD:** 0% (not tracked)
**NEW:** Synthetic recovery guarantees 100% tracking
**Status:** ✅ Will Pass

### Gate E: Dataset Realism (NEW)

**Target:** Failure rate 30-60% (not 100%)
**Method:** Controlled injection probability
**Status:** ✅ Will Pass

---

## 🚫 What to STOP Doing

1. ❌ Live browser replay on real websites during Phase 5
2. ❌ Trying to handle bot protection / CAPTCHA
3. ❌ DOM-based selectors without grounding model
4. ❌ Counting "partial" as "failure" in metrics
5. ❌ Scaling to 10,000 tasks before fixing fundamentals

---

## ✅ What to START Doing

1. ✅ Use Multimodal Mind2Web screenshots (offline)
2. ✅ Implement systematic failure injection
3. ✅ Generate synthetic recovery steps
4. ✅ Target 40% success / 30% fail / 30% recovery distribution
5. ✅ Validate with 100-task pilot first

---

## 📊 Expected Outcomes

### After Implementation

| Metric          | Current    | Target            | Status        |
| --------------- | ---------- | ----------------- | ------------- |
| Failure Rate    | 100%       | 30-60%            | ✅ Achievable |
| Recovery Rate   | 0%         | 55-65%            | ✅ Guaranteed |
| Error Page Rate | 9.1%       | 0%                | ✅ Eliminated |
| Dataset Size    | 99 steps   | 5,000+ steps      | ✅ Scalable   |
| Data Quality    | ❌ Invalid | ✅ Research-grade | ✅ Achievable |

---

## 🎯 Key Takeaway

**Switch from "broken live replay" to "controlled offline injection"**

This approach:

- ✅ Eliminates 100% failure problem
- ✅ Enables recovery tracking
- ✅ Creates balanced, realistic dataset
- ✅ Makes Phase 6-7 training possible
- ✅ Publishable quality

**Timeline:** 6 weeks to complete Phase 5 properly, then ready for training.

---

## 📝 Next Actions

See `PHASE5_TODO.md` for detailed implementation checklist.
