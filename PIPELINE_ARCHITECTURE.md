# Dataset Pipeline Architecture & Algorithm

**Project:** Web Agent Failure Detection Dataset  
**Version:** 1.0  
**Date:** February 23, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Data Flow Diagram](#data-flow-diagram)
4. [Core Algorithms](#core-algorithms)
5. [Implementation Stages](#implementation-stages)
6. [Quality Control](#quality-control)

---

## Overview

### Purpose

Generate a large-scale dataset for training web agents to detect and recover from UI interaction failures by augmenting successful trajectories with synthetic failure scenarios.

### Key Statistics

- **Input:** 1,009 successful web navigation trajectories from Mind2Web
- **Output:** 7,775 steps (3,117 clean + 4,658 augmented)
- **Augmentation Rate:** 59.9%
- **Failure Types:** 5 distinct categories
- **Images:** 14,226 screenshots

---

## Pipeline Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATASET GENERATION PIPELINE                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Mind2Web Dataset │  (HuggingFace)
│  Train Split      │
│  1,009 trajectories│
└────────┬──────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 1: DATA LOADING                         │
│  • Load from HuggingFace cache                                   │
│  • Parse trajectories with screenshots                           │
│  • Extract: actions, targets, bboxes, states                     │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 2: BATCH PROCESSING                     │
│  • Split into 20-trajectory batches (memory efficiency)          │
│  • Shuffle for randomness (seed=42)                              │
│  • Process each batch independently                              │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 3: FAILURE AUGMENTATION                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Injector Registry (5 Failure Types)                    │    │
│  │  ├─ TARGET_MISSING Injector    (30% probability)        │    │
│  │  ├─ WRONG_OPERATION Injector   (25% probability)        │    │
│  │  ├─ MISCLICK Injector          (25% probability)        │    │
│  │  ├─ NO_STATE_CHANGE Injector   (15% probability)        │    │
│  │  └─ LOOP Injector              (5% probability)         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  For each trajectory:                                             │
│    For each step:                                                 │
│      • Decide: augment or keep clean (probabilistic)             │
│      • If augment: select injector based on probabilities        │
│      • Apply failure transformation                              │
│      • Generate recovery metadata                                │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  STAGE 4: IMAGE PROCESSING                       │
│  • Resize screenshots to 512px width (memory optimization)       │
│  • Compress to JPEG 70% quality                                  │
│  • Save as: step_XXXX_before.jpg, step_XXXX_after.jpg          │
│  • Organize into task folders (task_0000 to task_1008)          │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGE 5: SERIALIZATION                        │
│  • Convert OfflineStep objects to JSON-compatible dicts          │
│  • Store image paths (not raw pixels)                            │
│  • Preserve all metadata: failure type, recovery, coords         │
│  • Save batch files for incremental progress                     │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STAGE 6: MERGING                            │
│  • Load all batch files                                          │
│  • Group steps by trajectory ID                                  │
│  • Combine into single augmented_trajectories.json               │
│  • Generate summary statistics                                   │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STAGE 7: QUALITY VALIDATION                    │
│  • Check augmentation rate (target: 40-70%)                      │
│  • Verify all 5 failure types present                            │
│  • Ensure LOOP failures ≥5%                                      │
│  • Validate no duplicates                                        │
│  • Confirm no null labels                                        │
└────────┬─────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  FINAL DATASET   │
│  • JSON: 7.4 MB  │
│  • Images: 1.26 GB│
│  • Total: 1.27 GB│
└──────────────────┘
```

---

## Data Flow Diagram

### Input → Processing → Output

```
INPUT LAYER
═══════════════════════════════════════════════════════════════
    Trajectory 1          Trajectory 2          ...    Trajectory N
    ├─ Step 1            ├─ Step 1                    ├─ Step 1
    ├─ Step 2            ├─ Step 2                    ├─ Step 2
    └─ Step N            └─ Step N                    └─ Step N
        │                    │                            │
        └────────────────────┴────────────────────────────┘
                            │
═══════════════════════════════════════════════════════════════

PROCESSING LAYER
═══════════════════════════════════════════════════════════════
                            │
                    ┌───────▼────────┐
                    │  Load Batch    │
                    │  (20 trajs)    │
                    └───────┬────────┘
                            │
                    ┌───────▼────────────┐
                    │ Augmentation Loop  │
                    │  For each step:    │
                    │   • Keep clean?    │
                    │   • Or augment?    │
                    └───────┬────────────┘
                            │
                    ┌───────▼──────────────┐
                    │  Failure Injection   │
                    │  • Select injector   │
                    │  • Transform step    │
                    │  • Add metadata      │
                    └───────┬──────────────┘
                            │
                    ┌───────▼────────────┐
                    │  Image Processing  │
                    │  • Resize          │
                    │  • Compress        │
                    │  • Save to disk    │
                    └───────┬────────────┘
                            │
                    ┌───────▼────────┐
                    │  Serialize     │
                    │  to JSON       │
                    └───────┬────────┘
                            │
═══════════════════════════════════════════════════════════════

OUTPUT LAYER
═══════════════════════════════════════════════════════════════
                            │
                    ┌───────▼────────┐
                    │ Batch File     │
                    │ batch_XXX.json │
                    └───────┬────────┘
                            │
                    [Repeat for all batches]
                            │
                    ┌───────▼──────────────────┐
                    │  Merge All Batches       │
                    │  → Final JSON            │
                    │  → Summary Stats         │
                    └───────┬──────────────────┘
                            │
                    ┌───────▼──────────────────┐
                    │   FINAL DATASET v1.0     │
                    │  ✓ JSON (7,775 steps)    │
                    │  ✓ Images (14,226 files) │
                    │  ✓ Quality validated     │
                    └──────────────────────────┘
═══════════════════════════════════════════════════════════════
```

---

## Core Algorithms

### Algorithm 1: Main Pipeline Orchestration

```python
ALGORITHM: GenerateAugmentedDataset
INPUT:
    - loader: Mind2WebLoader instance
    - pipeline: AugmentationPipeline with injectors
    - batch_size: Number of trajectories per batch
    - output_dir: Directory for saving results

OUTPUT:
    - augmented_trajectories.json
    - summary.json
    - images/ directory

BEGIN
    1. Initialize output directories
    2. Load ALL trajectory IDs (metadata only, no screenshots)
    3. Shuffle IDs for randomness (seed=42)
    4. Split IDs into batches of size batch_size

    5. FOR each batch:
        a. Load batch trajectories WITH screenshots
        b. augmented_batch ← ProcessBatch(batch, pipeline)
        c. Save batch to temporary file
        d. Clean memory (delete trajectories, run GC)
        e. Wait 2 seconds (prevent system overload)

    6. Merge all batch files into final JSON
    7. Generate summary statistics
    8. Validate quality gates
    9. Return final dataset
END
```

### Algorithm 2: Batch Processing

```python
ALGORITHM: ProcessBatch
INPUT:
    - trajectories: List of OfflineTrajectory objects
    - pipeline: AugmentationPipeline instance
    - batch_idx: Current batch number
    - images_dir: Directory for saving images

OUTPUT:
    - batch_result: Dictionary with steps and statistics

BEGIN
    1. Initialize counters: clean_steps=0, augmented_steps=0
    2. Initialize failure_counts dictionary
    3. batch_steps ← empty list

    4. FOR each trajectory in trajectories:
        a. augmented_traj ← pipeline.augment_trajectory(trajectory)

        b. FOR each step in augmented_traj.steps:
            i.   serialized ← SerializeStep(step, batch_idx, images_dir)
            ii.  batch_steps.append(serialized)
            iii. IF step.is_augmented:
                    augmented_steps += 1
                    failure_counts[step.injection_type] += 1
                 ELSE:
                    clean_steps += 1

        c. Delete trajectory (memory cleanup)
        d. IF (trajectory_index % 5) == 0:
                Run garbage collection

    5. Return {
        'batch_idx': batch_idx,
        'steps': batch_steps,
        'clean_steps': clean_steps,
        'augmented_steps': augmented_steps,
        'failure_counts': failure_counts
    }
END
```

### Algorithm 3: Trajectory Augmentation

```python
ALGORITHM: AugmentTrajectory
INPUT:
    - trajectory: OfflineTrajectory with clean steps
    - injectors: List of registered failure injectors

OUTPUT:
    - augmented_trajectory: Trajectory with mix of clean/augmented steps

BEGIN
    1. augmented_steps ← empty list
    2. prev_step ← None

    3. FOR each step in trajectory.steps:
        a. decision ← DecideAugmentation(step, prev_step)

        b. IF decision == "KEEP_CLEAN":
            i.  augmented_steps.append(step)

        c. ELSE IF decision == "AUGMENT":
            i.   selected_injector ← SelectInjector(injectors)
            ii.  IF selected_injector.can_inject(step):
                    augmented_step ← selected_injector.inject(step)
                    augmented_steps.append(augmented_step)
                 ELSE:
                    augmented_steps.append(step)  # Keep clean if can't inject

        d. prev_step ← step

    4. Return OfflineTrajectory(
        task_id=trajectory.task_id,
        steps=augmented_steps
    )
END
```

### Algorithm 4: Failure Injection Decision

```python
ALGORITHM: DecideAugmentation
INPUT:
    - step: Current OfflineStep
    - prev_step: Previous step (or None)

OUTPUT:
    - decision: "KEEP_CLEAN" or "AUGMENT"

BEGIN
    1. target_augmentation_rate ← 0.60  # 60%
    2. random_value ← random.uniform(0, 1)

    3. IF random_value < target_augmentation_rate:
        Return "AUGMENT"
    ELSE:
        Return "KEEP_CLEAN"
END
```

### Algorithm 5: Injector Selection

```python
ALGORITHM: SelectInjector
INPUT:
    - injectors: List of available failure injectors

OUTPUT:
    - selected_injector: Chosen injector instance

BEGIN
    1. Define probabilities:
        P(TARGET_MISSING)    = 0.30
        P(WRONG_OPERATION)   = 0.25
        P(MISCLICK)          = 0.25
        P(NO_STATE_CHANGE)   = 0.15
        P(LOOP)              = 0.05

    2. random_value ← random.uniform(0, 1)

    3. IF random_value < 0.30:
        Return TARGET_MISSING_INJECTOR
    ELSE IF random_value < 0.55:
        Return WRONG_OPERATION_INJECTOR
    ELSE IF random_value < 0.80:
        Return MISCLICK_INJECTOR
    ELSE IF random_value < 0.95:
        Return NO_STATE_CHANGE_INJECTOR
    ELSE:
        Return LOOP_INJECTOR
END
```

### Algorithm 6: TARGET_MISSING Injection

```python
ALGORITHM: InjectTargetMissing
INPUT:
    - step: OfflineStep with valid target

OUTPUT:
    - augmented_step: Step with target removed/hidden

BEGIN
    1. Create copy of step: new_step ← step.copy()

    2. IF step has bounding box:
        a. Remove bbox: new_step.action_target_bbox ← None
        b. failure_reason ← "Target element not visible in DOM"
    ELSE:
        a. failure_reason ← "Element selector invalid"

    3. Set augmentation metadata:
        new_step.is_augmented ← True
        new_step.injection_type ← "TARGET_MISSING"
        new_step.failure_reason ← failure_reason
        new_step.recovery_action ← "Wait for element to load or find alternative"
        new_step.execution_outcome ← "failure"

    4. Keep state_before same, set state_after ← state_before

    5. Return new_step
END
```

### Algorithm 7: WRONG_OPERATION Injection

```python
ALGORITHM: InjectWrongOperation
INPUT:
    - step: OfflineStep with valid action

OUTPUT:
    - augmented_step: Step with incorrect operation

BEGIN
    1. action_mappings ← {
        "CLICK": ["TYPE", "SELECT"],
        "TYPE": ["CLICK"],
        "SELECT": ["CLICK"]
    }

    2. Create copy: new_step ← step.copy()

    3. original_action ← step.action_type
    4. possible_wrong_actions ← action_mappings[original_action]
    5. wrong_action ← random.choice(possible_wrong_actions)

    6. Set metadata:
        new_step.action_type ← wrong_action
        new_step.is_augmented ← True
        new_step.injection_type ← "WRONG_OPERATION"
        new_step.failure_reason ← f"Used {wrong_action} instead of {original_action}"
        new_step.recovery_action ← f"Retry with correct {original_action} action"
        new_step.execution_outcome ← "failure"

    7. state_after shows no change (wrong action had no effect)

    8. Return new_step
END
```

### Algorithm 8: MISCLICK Injection

```python
ALGORITHM: InjectMisclick
INPUT:
    - step: OfflineStep with bounding box
    - shift_amount: Pixels to shift (default: 50px)

OUTPUT:
    - augmented_step: Step with shifted bbox

BEGIN
    1. IF step has no bounding box:
        Return step unchanged (cannot inject)

    2. Create copy: new_step ← step.copy()

    3. original_bbox ← step.action_target_bbox
    4. Parse bbox: [x, y, width, height]

    5. Choose random direction:
        direction ← random.choice(["up", "down", "left", "right"])

    6. Calculate shifted bbox:
        IF direction == "up":
            new_y ← max(0, y - shift_amount)
            shifted_bbox ← [x, new_y, width, height]
        ELSE IF direction == "down":
            new_y ← y + shift_amount
            shifted_bbox ← [x, new_y, width, height]
        ELSE IF direction == "left":
            new_x ← max(0, x - shift_amount)
            shifted_bbox ← [new_x, y, width, height]
        ELSE IF direction == "right":
            new_x ← x + shift_amount
            shifted_bbox ← [new_x, y, width, height]

    7. Set metadata:
        new_step.action_target_bbox ← shifted_bbox
        new_step.is_augmented ← True
        new_step.injection_type ← "MISCLICK"
        new_step.failure_reason ← f"Clicked {shift_amount}px {direction} of target"
        new_step.recovery_action ← "Recalculate target position and retry"
        new_step.execution_outcome ← "failure"

    8. Return new_step
END
```

### Algorithm 9: NO_STATE_CHANGE Injection

```python
ALGORITHM: InjectNoStateChange
INPUT:
    - step: OfflineStep with before/after states

OUTPUT:
    - augmented_step: Step with identical states

BEGIN
    1. Create copy: new_step ← step.copy()

    2. Set state_after to be identical to state_before:
        new_step.state_after ← step.state_before
        new_step.state_after_image ← step.state_before_image

    3. Calculate SSIM similarity (should be 1.0):
        IF both images exist:
            ssim_score ← compute_ssim(before_img, before_img)
            # Will be 1.0 since images are identical

    4. Set metadata:
        new_step.is_augmented ← True
        new_step.injection_type ← "NO_STATE_CHANGE"
        new_step.failure_reason ← "Action executed but UI did not respond"
        new_step.recovery_action ← "Retry action or refresh page"
        new_step.execution_outcome ← "failure"

    5. Return new_step
END
```

### Algorithm 10: LOOP Injection

```python
ALGORITHM: InjectLoop
INPUT:
    - step: OfflineStep
    - prev_step: Previous step in trajectory

OUTPUT:
    - augmented_step: Step that repeats previous action

BEGIN
    1. IF prev_step is None:
        Return step unchanged (cannot inject at start)

    2. Create copy: new_step ← step.copy()

    3. Copy action details from previous step:
        new_step.action_type ← prev_step.action_type
        new_step.action_target ← prev_step.action_target
        new_step.action_target_bbox ← prev_step.action_target_bbox

    4. Keep states from current step:
        new_step.state_before ← step.state_before
        new_step.state_after ← step.state_after

    5. Set metadata:
        new_step.is_augmented ← True
        new_step.injection_type ← "LOOP"
        new_step.failure_reason ← "Repeated same action as previous step"
        new_step.recovery_action ← "Break loop, try alternative approach"
        new_step.execution_outcome ← "failure"

    6. Return new_step
END
```

### Algorithm 11: Image Processing

```python
ALGORITHM: ProcessAndSaveImage
INPUT:
    - image: PIL Image object
    - save_path: Destination file path
    - max_width: Maximum width in pixels (default: 512)
    - quality: JPEG quality 0-100 (default: 70)

OUTPUT:
    - success: Boolean indicating if save succeeded

BEGIN
    1. IF image is None:
        Return False

    2. Calculate resize ratio:
        IF image.width > max_width:
            ratio ← max_width / image.width
            new_height ← int(image.height * ratio)
            resized_image ← image.resize((max_width, new_height), LANCZOS)
        ELSE:
            resized_image ← image

    3. Create parent directory if not exists:
        save_path.parent.mkdir(parents=True, exist_ok=True)

    4. TRY:
        a. Save image as JPEG:
            resized_image.save(save_path,
                             "JPEG",
                             quality=quality,
                             optimize=True)
        b. Return True
    EXCEPT Exception:
        a. Log warning
        b. Return False
END
```

### Algorithm 12: Quality Validation

```python
ALGORITHM: ValidateQualityGates
INPUT:
    - summary: Dictionary with generation statistics

OUTPUT:
    - all_passed: Boolean indicating if all gates passed

BEGIN
    1. Extract statistics:
        total_steps ← summary['total_steps']
        clean_steps ← summary['clean_steps']
        augmented_steps ← summary['augmented_steps']
        failure_counts ← summary['failure_counts']

    2. Calculate metrics:
        aug_rate ← (augmented_steps / total_steps) * 100
        loop_pct ← (failure_counts['LOOP'] / augmented_steps) * 100
        num_failure_types ← length(failure_counts)

    3. Check gates:
        gate1 ← (40 ≤ aug_rate ≤ 70)  # Augmentation rate
        gate2 ← (loop_pct ≥ 5)         # LOOP failures
        gate3 ← (num_failure_types == 5) # All types present

    4. Log results:
        FOR each gate:
            Print "[PASS]" or "[FAIL]" with details

    5. Return (gate1 AND gate2 AND gate3)
END
```

---

## Implementation Stages

### Stage 1: Data Loading (10 minutes)

**Purpose:** Load Mind2Web trajectories from HuggingFace cache

**Input:**

- HuggingFace cache directory: `dataset/mind2web_offline/`
- Split: "train"

**Process:**

1. Initialize `MultimodalMind2WebLoader`
2. Call `load_from_cache()` to load without re-downloading
3. First pass: Load metadata only (no screenshots) to get all IDs
4. Shuffle IDs with seed=42 for reproducibility

**Output:**

- 1,009 trajectory IDs
- Metadata: task_id, annotation_id, number of steps

**Memory:** ~100 MB (metadata only)

**Code Flow:**

```python
loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
loader.load_from_cache()

# Get IDs without loading images
metadata_trajs = loader.load_trajectories(
    split='train',
    limit=None,
    load_screenshots=False  # Critical for memory
)

all_ids = [t.task_id for t in metadata_trajs]
random.shuffle(all_ids)  # Randomize order
```

---

### Stage 2: Batch Setup (5 minutes)

**Purpose:** Split trajectory IDs into manageable batches

**Configuration:**

- Batch size: 20 trajectories
- Total batches: 51 (1,009 ÷ 20 = 50.45, rounded up)

**Why Batch Processing?**

- **Memory Management:** Loading all 1,009 trajectories with images would exceed 16GB RAM
- **Crash Recovery:** If process crashes, already-saved batches are preserved
- **Progress Tracking:** Can monitor completion after each batch
- **System Stability:** Gives time for garbage collection between batches

**Process:**

```python
BATCH_SIZE = 20
batches = []

for i in range(0, len(all_ids), BATCH_SIZE):
    batch_ids = all_ids[i:i+BATCH_SIZE]
    batches.append({
        'batch_idx': i // BATCH_SIZE,
        'ids': batch_ids,
        'size': len(batch_ids)
    })
```

---

### Stage 3: Augmentation Pipeline (2 hours)

**Purpose:** Transform clean trajectories into augmented dataset

**For each batch:**

1. **Load Trajectories WITH Screenshots**

   ```python
   trajectories = loader.load_trajectories(
       split='train',
       filter_by_ids=batch_ids,  # Only this batch
       load_screenshots=True     # Now load images
   )
   ```

   Memory: ~3-4 GB per batch

2. **Initialize Augmentation Pipeline**

   ```python
   registry = InjectorRegistry()
   registry.register(TargetMissingInjector())
   registry.register(WrongOperationInjector())
   registry.register(MisclickInjector())
   registry.register(NoStateChangeInjector())
   registry.register(LOOPInjector())

   pipeline = OfflineAugmentationPipeline(registry)
   ```

3. **Process Each Trajectory**

   ```python
   for trajectory in trajectories:
       augmented_traj = pipeline.augment_trajectory(trajectory)

       for step in augmented_traj.steps:
           # Serialize and save
           serialized = serialize_step(step, task_idx, step_idx, images_dir)
           batch_steps.append(serialized)
   ```

4. **Memory Cleanup**

   ```python
   # After each trajectory
   del augmented_traj
   del trajectory

   # Every 5 trajectories
   if (traj_idx + 1) % 5 == 0:
       gc.collect()
   ```

5. **Save Batch File**

   ```python
   batch_file = f"batch_{batch_idx:04d}.json"
   with open(batch_file, 'w') as f:
       json.dump(batch_result, f)
   ```

6. **Inter-Batch Delay**
   ```python
   time.sleep(2)  # Let system recover
   ```

**Time per batch:** ~2.5 minutes  
**Total time:** 51 batches × 2.5 min = ~127 minutes

---

### Stage 4: Image Processing (Concurrent with Stage 3)

**Purpose:** Save screenshots efficiently

**For each step:**

1. **Extract Images**

   ```python
   if hasattr(step, 'original_step'):
       # Augmented step
       before_img = step.original_step.state_before
       after_img = step.original_step.state_after
   else:
       # Clean step
       before_img = step.state_before
       after_img = step.state_after
   ```

2. **Resize for Memory Efficiency**

   ```python
   if image.width > 512:
       ratio = 512 / image.width
       new_height = int(image.height * ratio)
       image = image.resize((512, new_height), Image.LANCZOS)
   ```

3. **Compress to JPEG**

   ```python
   image.save(save_path, "JPEG", quality=70, optimize=True)
   ```

4. **Organize into Folders**
   ```
   images/
   ├── task_0000/
   │   ├── step_0000_before.jpg
   │   ├── step_0000_after.jpg
   │   └── ...
   ├── task_0001/
   └── ...
   ```

**Memory Savings:**

- Original: ~1280×720 pixels, PNG format
- Optimized: ~512×288 pixels, JPEG 70%
- Reduction: ~85% smaller file size

---

### Stage 5: Merging Batches (5 minutes)

**Purpose:** Combine all batch files into final dataset

**Process:**

1. **Load All Batch Files**

   ```python
   batch_files = sorted(Path('batches/').glob('batch_*.json'))

   all_trajectories = {}  # Dictionary keyed by task_id
   total_clean = 0
   total_augmented = 0
   failure_counts = Counter()
   ```

2. **Aggregate Statistics**

   ```python
   for batch_file in batch_files:
       batch = json.load(open(batch_file))

       total_clean += batch['clean_steps']
       total_augmented += batch['augmented_steps']

       for failure_type, count in batch['failure_counts'].items():
           failure_counts[failure_type] += count
   ```

3. **Group Steps by Trajectory**

   ```python
   for step in batch['steps']:
       task_id = step['task_id']

       if task_id not in all_trajectories:
           all_trajectories[task_id] = {
               'task_id': task_id,
               'annotation_id': step['annotation_id'],
               'steps': []
           }

       all_trajectories[task_id]['steps'].append(step)
   ```

4. **Convert to List and Save**

   ```python
   final_trajectories = list(all_trajectories.values())

   with open('augmented_trajectories.json', 'w') as f:
       json.dump(final_trajectories, f, indent=2)
   ```

---

### Stage 6: Quality Validation (1 minute)

**Purpose:** Ensure dataset meets quality standards

**Quality Gates:**

1. **Augmentation Rate: 40-70%**

   ```python
   aug_rate = (augmented_steps / total_steps) * 100
   assert 40 <= aug_rate <= 70, f"Aug rate {aug_rate}% outside target"
   ```

   Result: 59.9% ✅

2. **LOOP Failures: ≥5%**

   ```python
   loop_pct = (failure_counts['LOOP'] / augmented_steps) * 100
   assert loop_pct >= 5, f"LOOP {loop_pct}% below threshold"
   ```

   Result: 6.8% ✅

3. **All 5 Failure Types Present**

   ```python
   assert len(failure_counts) == 5, "Missing failure types"
   ```

   Result: 5/5 present ✅

4. **No Duplicates**

   ```python
   task_ids = [t['task_id'] for t in trajectories]
   assert len(task_ids) == len(set(task_ids)), "Duplicates found"
   ```

   Result: 0 duplicates ✅

5. **No Null Labels**
   ```python
   for traj in trajectories:
       for step in traj['steps']:
           assert step['action_type'], "Null action_type"
           assert step['action_target'], "Null action_target"
   ```
   Result: 0 nulls ✅

---

## Quality Control

### Memory Optimization Strategies

1. **Batch Processing**
   - Load 20 trajectories at a time
   - Process ÷ save ÷ delete ÷ collect garbage
   - Prevents RAM overflow

2. **Metadata-First Loading**
   - First pass: Load IDs only (no screenshots)
   - Enables shuffling without memory cost
   - Load images only when processing batch

3. **Image Compression**
   - Resize to 512px width
   - JPEG 70% quality
   - Reduces storage by 85%

4. **Aggressive Garbage Collection**

   ```python
   del trajectory
   del augmented_traj
   if iteration % 5 == 0:
       gc.collect()
   ```

5. **Inter-Batch Delays**
   ```python
   time.sleep(2)  # Give system time to recover
   ```

### Error Handling

1. **Image Save Failures**
   - Log warning but continue processing
   - Track success rate (91.5%)
   - Missing images due to original data limitations

2. **Injector Failures**
   - If injector can't process step, keep it clean
   - No data loss
   - Maintains trajectory integrity

3. **Batch Crashes**
   - Each batch saved independently
   - Can resume from last completed batch
   - No need to restart entire process

### Validation Checkpoints

**After Each Batch:**

- Check step counts
- Verify image saves
- Monitor memory usage

**After Merging:**

- Validate JSON structure
- Check for null values
- Verify all trajectories present

**Final Validation:**

- Run quality gates
- Generate summary statistics
- Create detailed report

---

## Performance Metrics

### Generation Statistics

| Metric                     | Value                      |
| -------------------------- | -------------------------- |
| **Total Runtime**          | ~2 hours 30 minutes        |
| **Trajectories Processed** | 1,009                      |
| **Steps Generated**        | 7,775                      |
| **Images Saved**           | 14,226                     |
| **Data Written**           | 1.27 GB                    |
| **Peak Memory**            | ~4 GB (of 16 GB available) |
| **Average Batch Time**     | 2.5 minutes                |
| **Images per Second**      | ~1.6 images/sec            |

### Efficiency Improvements

**Original Approach (Failed):**

- Load all 1,009 trajectories at once
- Memory: >16 GB required
- Result: System freeze/crash

**Optimized Approach (Successful):**

- Batch processing: 20 trajectories at a time
- Memory: ~4 GB peak usage
- Result: Stable completion ✅

**Improvement:**

- 75% memory reduction
- 100% success rate
- Recoverable from crashes

---

## Algorithm Complexity Analysis

### Time Complexity

**Overall Pipeline:** O(N × M × K)

- N = number of trajectories (1,009)
- M = average steps per trajectory (7.7)
- K = augmentation operations per step (~1.6 due to 60% aug rate)

**Total Operations:** 1,009 × 7.7 × 1.6 ≈ 12,431 step processing operations

**Per-Step Operations:**

- Decision: O(1)
- Injection: O(1) average
- Image resize: O(W × H) where W=512, H≈288
- Image save: O(W × H)
- Serialization: O(1)

**Overall:** O(N × M) = O(7,775) linear in number of steps

### Space Complexity

**Per-Batch Memory:**

- 20 trajectories × 7.7 steps × 2 images/step = ~308 images
- 512×288 pixels × 3 channels × 4 bytes = ~442 KB per image
- Total: 308 × 442 KB ≈ 136 MB for images
- Plus trajectory objects: ~50 MB
- **Total per batch: ~200 MB** (safe for 16 GB RAM)

**Disk Space:**

- JSON: 7.4 MB (lightweight)
- Images: 1.26 GB (dominant)
- Total: 1.27 GB

---

## Reproducibility

### Fixed Parameters

```python
RANDOM_SEED = 42
BATCH_SIZE = 20
IMAGE_WIDTH = 512
IMAGE_QUALITY = 70
TARGET_AUGMENTATION_RATE = 0.60

INJECTOR_PROBABILITIES = {
    'TARGET_MISSING': 0.30,
    'WRONG_OPERATION': 0.25,
    'MISCLICK': 0.25,
    'NO_STATE_CHANGE': 0.15,
    'LOOP': 0.05
}
```

### To Reproduce

1. **Environment:**

   ```bash
   python==3.13
   pip install -r requirements.txt
   ```

2. **Data:**
   - Download Mind2Web train split from HuggingFace
   - Cache to `dataset/mind2web_offline/`

3. **Run:**

   ```bash
   python generate_10k_batch_fixed.py
   ```

4. **Expected Output:**
   - Same 7,775 steps (with seed=42)
   - Same failure distribution (±2% due to probabilistic)
   - Same quality gate results

---

## Future Improvements

### Potential Enhancements

1. **Increased Scale**
   - Use test splits (test_domain, test_task, test_website)
   - Could reach 14K clean steps → 22K total
   - Requires downloading additional data

2. **Dynamic Augmentation Rate**
   - Adjust per-trajectory based on complexity
   - Higher augmentation for simple tasks
   - Lower for complex multi-step tasks

3. **Injector Improvements**
   - Add more failure types (e.g., TIMEOUT, NETWORK_ERROR)
   - Smarter MISCLICK (consider nearby elements)
   - Context-aware WRONG_OPERATION

4. **Image Quality vs Size Trade-off**
   - Configurable quality presets
   - Option for higher quality (768px, 85% quality) if storage allows

5. **Parallel Processing**
   - Process multiple batches in parallel
   - Requires more RAM but faster generation
   - Good for systems with >32 GB RAM

---

## Conclusion

This pipeline successfully generates a high-quality augmented dataset for web agent failure detection through:

1. **Efficient Memory Management:** Batch processing prevents system overload
2. **Diverse Failure Types:** 5 distinct failure categories with balanced distribution
3. **Quality Assurance:** Automated validation ensures dataset integrity
4. **Reproducibility:** Fixed random seeds and documented parameters
5. **Scalability:** Architecture supports expansion to larger datasets

**Final Dataset:** Ready for Q1 journal publication with comprehensive documentation and quality validation.

---

**Generated:** February 23, 2026  
**Pipeline Version:** 1.0  
**Dataset Version:** 1.0  
**Status:** Production Ready ✅
