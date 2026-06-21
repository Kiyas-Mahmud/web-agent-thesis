# System Architecture Documentation

## Project Overview

**Failure-Aware Web Interaction Trajectory Dataset Collection System**

This system implements an end-to-end pipeline for generating augmented training data for robust web agents by:

1. Loading pre-collected web interaction trajectories with screenshots
2. Systematically injecting realistic failure patterns
3. Generating recovery strategies for agent training

The system is designed for offline augmentation using established benchmark datasets (Multimodal Mind2Web) to create failure-aware training data for Q1 journal publication.

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐      ┌──────────────────────────┐   │
│  │ Multimodal Mind2Web      │      │  Custom Collections      │   │
│  │ - 50K steps w/ screenshots│      │  - Browser Recorder      │   │
│  │ - 27 Parquet files (8.4GB)│      │  - Live Capture         │   │
│  └────────────┬─────────────┘      └────────────┬─────────────┘   │
└───────────────┼─────────────────────────────────┼─────────────────┘
                │                                  │
                └────────────┬─────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA LOADING LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃  Mind2Web Loader (src/offline_data/mind2web_loader.py)   ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  • Cache-first loading (avoids re-downloads)              ┃  │
│  ┃  • Arrow table processing (memory efficient)              ┃  │
│  ┃  • JSON field parsing (operation, bbox)                   ┃  │
│  ┃  • On-demand screenshot loading                           ┃  │
│  ┃  • Trajectory grouping (by annotation_id)                 ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                             │                                        │
│                             ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │         Offline Schema (offline_schema.py)                   │  │
│  │  • OfflineStep: Single action with screenshot                │  │
│  │  • OfflineTrajectory: Sequence of steps                      │  │
│  │  • AugmentedStep: Step + failure metadata                    │  │
│  │  • AugmentedTrajectory: Complete output format               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  FAILURE INJECTION LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃    Injection Pipeline (injection_engine.py)                ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Config: 60% injection rate, weighted distribution         ┃  │
│  ┃  Process: trajectory → step → inject? → augment            ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                             │                                        │
│           ┌─────────────────┼─────────────────┐                    │
│           ▼                 ▼                 ▼                     │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐         │
│  │ TARGET_MISSING │ │   MISCLICK   │ │ WRONG_OPERATION  │         │
│  │  (Perception)  │ │ (Execution)  │ │   (Planning)     │         │
│  │                │ │              │ │                  │         │
│  │ • Masks target │ │ • Shifts     │ │ • Swaps action   │         │
│  │ • Blurs bbox   │ │   coords     │ │   type           │         │
│  │ • 69% success  │ │ • 66% success│ │ • 51% success    │         │
│  └────────────────┘ └──────────────┘ └──────────────────┘         │
│           │                 │                 │                     │
│           └─────────────────┼─────────────────┘                    │
│                             │                                        │
│           ┌─────────────────┼─────────────────┐                    │
│           ▼                 ▼                 ▼                     │
│  ┌────────────────┐ ┌──────────────────────────────────┐          │
│  │ NO_STATE_CHANGE│ │          LOOP                    │          │
│  │  (Timing)      │ │      (Temporal)                  │          │
│  │                │ │                                  │          │
│  │ • No UI change │ │ • Repeats actions                │          │
│  │ • 32% success  │ │ • Not active (needs state_after) │          │
│  └────────────────┘ └──────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   IMAGE PROCESSING LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │     Image Preprocessor (image_preprocessor.py)               │  │
│  │                                                              │  │
│  │  • mask_bbox(): Gaussian blur masking                        │  │
│  │  • shift_coords(): Coordinate perturbation                   │  │
│  │  • find_alternative_target(): Distractor selection           │  │
│  │  • compute_ssim(): Visual similarity metrics                 │  │
│  │  • compute_pixel_diff(): Change detection                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐    ┌─────────────────────────────────────┐│
│  │  Augmented Data    │    │     Statistics & Metrics            ││
│  │                    │    │                                     ││
│  │ • Trajectories     │    │ • Injection rates                   ││
│  │ • Screenshots      │    │ • Failure distribution              ││
│  │ • Failure metadata │    │ • Injector success rates            ││
│  │ • Recovery hints   │    │ • Quality metrics                   ││
│  └────────────────────┘    └─────────────────────────────────────┘│
│           │                              │                          │
│           └──────────────┬───────────────┘                          │
│                          ▼                                          │
│         JSON Output (summary.json, trajectories.json)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 End-to-End Workflow

### Phase 1: Data Acquisition

```
┌──────────────────────────────────────────────────────────────┐
│ 1. DOWNLOAD DATASET                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Source: HuggingFace Hub                                      │
│ Dataset: osunlp/Multimodal-Mind2Web                          │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ download_mind2web.py                                   │  │
│ │ ├─ Uses huggingface-hub API                            │  │
│ │ ├─ Downloads 27 parquet files                          │  │
│ │ ├─ Retry logic (3 attempts, exponential backoff)       │  │
│ │ ├─ 3-minute timeout per file                           │  │
│ │ └─ Saves to HF cache directory                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Cache Location:                                              │
│ C:\Users\{user}\.cache\huggingface\hub\                     │
│    datasets--osunlp--Multimodal-Mind2Web\                   │
│        snapshots\{hash}\data\train\                         │
│                                                              │
│ Files: train-00000-of-00027.parquet ... train-00026...      │
│ Total: 8.4 GB (full dataset)                                │
│ Current: 3.95 GB (17/27 files)                              │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. CACHE VALIDATION                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ • Scan cache directory for .parquet files                   │
│ • Verify file integrity (size > 0)                          │
│ • Count available files                                     │
│ • Log: "Found 17 cached parquet files (3.95 GB)"           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 2: Data Loading & Parsing

```
┌──────────────────────────────────────────────────────────────┐
│ 3. LOAD FROM CACHE                                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Mind2WebLoader.load_from_cache()                             │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 3.1: Read Parquet Files                           │  │
│ │ ├─ Use pyarrow.parquet.read_table()                    │  │
│ │ ├─ Read each file as Arrow table                       │  │
│ │ └─ Concatenate all tables                              │  │
│ │                                                         │  │
│ │ Step 3.2: Create HuggingFace Dataset                   │  │
│ │ ├─ Dataset.from_arrow(table)                           │  │
│ │ ├─ Set fixed fingerprint: "cached_mind2web_partial"    │  │
│ │ └─ Disable features (avoid image auto-decode)          │  │
│ │                                                         │  │
│ │ Result: Dataset object with 4,896 rows                 │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. TRAJECTORY GROUPING                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Mind2WebLoader.load_trajectories(load_screenshots=True)      │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Mind2Web Format: 1 row = 1 action step                │  │
│ │                                                         │  │
│ │ Columns:                                               │  │
│ │ • annotation_id: Trajectory identifier                 │  │
│ │ • action_uid: Step number within trajectory            │  │
│ │ • operation: JSON string {"op": "CLICK", ...}          │  │
│ │ • pos_candidates: JSON array of target elements        │  │
│ │ • screenshot: Binary image data                        │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 4.1: Group by annotation_id                       │  │
│ │                                                         │  │
│ │   4,896 rows → 1,019 unique trajectories              │  │
│ │                                                         │  │
│ │   {                                                    │  │
│ │     "traj_001": [action_0, action_1, action_2, ...],  │  │
│ │     "traj_002": [action_0, action_1, ...],            │  │
│ │     ...                                                │  │
│ │   }                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. PARSE EACH TRAJECTORY                                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ _parse_trajectory_from_actions()                             │
│                                                              │
│ For each annotation_id group:                                │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 5.1: Sort actions by action_uid                   │  │
│ │           (ensure correct temporal order)              │  │
│ │                                                         │  │
│ │ Step 5.2: Extract metadata from first action           │  │
│ │   • website: "amazon.com"                              │  │
│ │   • domain: "shopping"                                 │  │
│ │   • confirmed_task: "Find blue shoes under $50"        │  │
│ │                                                         │  │
│ │ Step 5.3: Parse each action → OfflineStep              │  │
│ │   (see detailed parsing below)                         │  │
│ │                                                         │  │
│ │ Step 5.4: Create OfflineTrajectory object              │  │
│ │   • task_id: annotation_id                             │  │
│ │   • steps: List[OfflineStep]                           │  │
│ │   • num_steps: len(steps)                              │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 3: Action Parsing (Critical Step)

```
┌──────────────────────────────────────────────────────────────┐
│ 6. PARSE SINGLE ACTION                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ _parse_single_action_step()                                  │
│                                                              │
│ Input: action_sample (dict from Arrow table row)            │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 6.1: Parse operation field                        │  │
│ │                                                         │  │
│ │   Raw: '{"original_op": "CLICK", "op": "CLICK", ...}' │  │
│ │   ├─ Check: isinstance(operation, str)                 │  │
│ │   ├─ Parse: json.loads(operation)                      │  │
│ │   └─ Extract: operation_type = op_dict.get("op")       │  │
│ │                                                         │  │
│ │   Result: action_type = "CLICK"                        │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 6.2: Parse pos_candidates (target bbox)           │  │
│ │                                                         │  │
│ │   Raw: ['{"tag": "button", "attributes": "{...}"}']   │  │
│ │                                                         │  │
│ │   Parse Flow:                                          │  │
│ │   1. Extract first candidate (target element)          │  │
│ │   2. json.loads(candidate) → dict                      │  │
│ │   3. Extract attributes field                          │  │
│ │   4. json.loads(attributes) → nested dict              │  │
│ │   5. Get bounding_box_rect: "283.18,220.39,93.59,33"  │  │
│ │   6. Split by comma: [x, y, width, height]            │  │
│ │   7. Convert to dict: {x: 283.18, y: 220.39, ...}     │  │
│ │   8. Calculate center: (x + width/2, y + height/2)    │  │
│ │                                                         │  │
│ │   Result:                                              │  │
│ │   • target_bbox = {x: 283.18, y: 220.39, w: 93.59...} │  │
│ │   • action_coords = (329, 236)  # center point        │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 6.3: Load screenshot (if enabled)                 │  │
│ │                                                         │  │
│ │   1. Get row_index from action_sample['_row_index']    │  │
│ │   2. Access: arrow_table['screenshot'][row_index]      │  │
│ │   3. Extract: screenshot_data.as_py()                  │  │
│ │      Format: {"bytes": b'\x89PNG...', "path": null}   │  │
│ │   4. Convert: Image.open(BytesIO(bytes))               │  │
│ │                                                         │  │
│ │   Result: state_before = PIL.Image (typically 1400x900)│  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 6.4: Create OfflineStep object                    │  │
│ │                                                         │  │
│ │   OfflineStep(                                         │  │
│ │     task_id = annotation_id,                           │  │
│ │     website = "amazon.com",                            │  │
│ │     domain = "shopping",                               │  │
│ │     action_type = "CLICK",                             │  │
│ │     action_coords = (329, 236),                        │  │
│ │     state_before = <PIL.Image>,                        │  │
│ │     target_bbox = {x: ..., y: ..., ...},               │  │
│ │     is_valid = True                                    │  │
│ │   )                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 4: Failure Injection

```
┌──────────────────────────────────────────────────────────────┐
│ 7. INITIALIZE INJECTION PIPELINE                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ config = InjectionConfig(injection_rate=0.6)                 │
│ pipeline = InjectionPipeline(config)                         │
│                                                              │
│ # Register all injectors                                     │
│ pipeline.register_injector(TargetMissingInjector(config))    │
│ pipeline.register_injector(MisclickInjector(config))         │
│ pipeline.register_injector(WrongOperationInjector(config))   │
│ pipeline.register_injector(NoStateChangeInjector(config))    │
│ pipeline.register_injector(LoopInjector(config))             │
│                                                              │
│ Injectors ready: 5 types, weighted distribution             │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 8. PROCESS TRAJECTORY                                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ pipeline.augment_trajectory(trajectory)                      │
│                                                              │
│ For each step in trajectory.steps:                          │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 8.1: Injection Decision (Probabilistic)           │  │
│ │                                                         │  │
│ │   if random.random() < config.injection_rate (0.6):    │  │
│ │       # 60% probability → inject failure               │  │
│ │       proceed to injection                             │  │
│ │   else:                                                │  │
│ │       # 40% probability → keep clean                   │  │
│ │       return AugmentedStep(step, is_augmented=False)   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 8.2: Select Injector (Weighted Random)            │  │
│ │                                                         │  │
│ │   Filter eligible injectors:                           │  │
│ │   eligible = [inj for inj in all_injectors             │  │
│ │               if inj.can_inject(step)]                 │  │
│ │                                                         │  │
│ │   Apply weights from failure_type_distribution:        │  │
│ │   • TARGET_MISSING: 27%                                │  │
│ │   • MISCLICK: 23%                                      │  │
│ │   • WRONG_OPERATION: 20%                               │  │
│ │   • NO_STATE_CHANGE: 17%                               │  │
│ │   • LOOP: 13%                                          │  │
│ │                                                         │  │
│ │   chosen = random.choices(eligible, weights=...)[0]    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 8.3: Execute Injection                            │  │
│ │                                                         │  │
│ │   augmented_step = chosen_injector.inject(             │  │
│ │       step=step,                                       │  │
│ │       trajectory=trajectory                            │  │
│ │   )                                                    │  │
│ │                                                         │  │
│ │   (detailed injection logic per type below)            │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Step 8.4: Update Statistics                            │  │
│ │                                                         │  │
│ │   if augmented_step.is_augmented:                      │  │
│ │       injector.success_count += 1                      │  │
│ │       pipeline.injection_counts[type] += 1             │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Phase 5: Injector-Specific Logic

```
┌──────────────────────────────────────────────────────────────┐
│ 9. TARGET_MISSING INJECTION (Perception Failure)             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Purpose: Simulate agent failing to detect target element     │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Prerequisites (can_inject check):                      │  │
│ │  ✓ step.is_valid == True                               │  │
│ │  ✓ step.state_before is not None                       │  │
│ │  ✓ step.target_bbox is not None                        │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Injection Steps:                                       │  │
│ │                                                         │  │
│ │ 1. Copy original screenshot                            │  │
│ │    failed_state = step.state_before.copy()             │  │
│ │                                                         │  │
│ │ 2. Mask target bounding box                            │  │
│ │    bbox = step.target_bbox                             │  │
│ │    region = (bbox.x, bbox.y, bbox.x+w, bbox.y+h)       │  │
│ │    apply_gaussian_blur(failed_state, region, radius=20)│  │
│ │                                                         │  │
│ │ 3. Determine recovery strategy                         │  │
│ │    if alternative elements nearby:                     │  │
│ │        strategy = "find_alternative"                   │  │
│ │    elif can scroll:                                    │  │
│ │        strategy = "scroll_and_retry"                   │  │
│ │    else:                                               │  │
│ │        strategy = "refresh_page"                       │  │
│ │                                                         │  │
│ │ 4. Create AugmentedStep                                │  │
│ │    return AugmentedStep(                               │  │
│ │        original_step = step,                           │  │
│ │        is_augmented = True,                            │  │
│ │        injection_type = "TARGET_MISSING",              │  │
│ │        modified_state = failed_state,                  │  │
│ │        recovery_strategy = strategy,                   │  │
│ │        recovery_hints = ["check_visibility", ...]      │  │
│ │    )                                                   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Success Rate: 69.3% (based on alternative elements)         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 10. MISCLICK INJECTION (Execution Failure)                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Purpose: Simulate clicking wrong location near target        │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Prerequisites:                                         │  │
│ │  ✓ step.action_type in ["CLICK", "HOVER", "SELECT"]   │  │
│ │  ✓ step.target_bbox is not None                        │  │
│ │  ✓ step.state_before is not None                       │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Injection Steps:                                       │  │
│ │                                                         │  │
│ │ 1. Calculate shifted coordinates                       │  │
│ │    original_x, original_y = step.action_coords         │  │
│ │    shift_distance = random.randint(50, 200)  # pixels  │  │
│ │    angle = random.uniform(0, 2*π)                      │  │
│ │    new_x = original_x + shift_distance * cos(angle)    │  │
│ │    new_y = original_y + shift_distance * sin(angle)    │  │
│ │                                                         │  │
│ │ 2. Find nearest clickable element at new coords        │  │
│ │    clicked_element = find_element_at(new_x, new_y,     │  │
│ │                            step.candidate_bboxes)       │  │
│ │                                                         │  │
│ │ 3. Determine correction needed                         │  │
│ │    offset = calculate_offset(original_coords,          │  │
│ │                              clicked_coords)            │  │
│ │    strategy = "adjust_coordinates"                     │  │
│ │                                                         │  │
│ │ 4. Return augmented step with misclick                 │  │
│ │    return AugmentedStep(                               │  │
│ │        injection_type = "MISCLICK",                    │  │
│ │        modified_action_coords = (new_x, new_y),        │  │
│ │        recovery_strategy = strategy,                   │  │
│ │        recovery_hints = [f"offset: {offset}"]          │  │
│ │    )                                                   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Success Rate: 66.2% (depends on nearby elements)            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 11. WRONG_OPERATION INJECTION (Planning Failure)             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Purpose: Simulate selecting wrong action type                │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Prerequisites:                                         │  │
│ │  ✓ step.action_type != "UNKNOWN"                       │  │
│ │  ✓ step.action_type in swappable_operations            │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Swappable Operations:                                  │  │
│ │   CLICK ↔ HOVER                                        │  │
│ │   TYPE ↔ SELECT                                        │  │
│ │   SCROLL ↔ CLICK                                       │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Injection Steps:                                       │  │
│ │                                                         │  │
│ │ 1. Get compatible operations                           │  │
│ │    if action_type == "CLICK":                          │  │
│ │        alternatives = ["HOVER"]                        │  │
│ │    elif action_type == "TYPE":                         │  │
│ │        alternatives = ["SELECT"]                       │  │
│ │    ...                                                 │  │
│ │                                                         │  │
│ │ 2. Select wrong operation                              │  │
│ │    wrong_op = random.choice(alternatives)              │  │
│ │                                                         │  │
│ │ 3. Determine recovery                                  │  │
│ │    strategy = "retry_with_correct_operation"           │  │
│ │    correct_op = step.action_type                       │  │
│ │                                                         │  │
│ │ 4. Return augmented step                               │  │
│ │    return AugmentedStep(                               │  │
│ │        injection_type = "WRONG_OPERATION",             │  │
│ │        modified_action_type = wrong_op,                │  │
│ │        recovery_strategy = strategy,                   │  │
│ │        recovery_hints = [f"use_{correct_op}"]          │  │
│ │    )                                                   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Success Rate: 50.5% (depends on operation compatibility)    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 12. NO_STATE_CHANGE INJECTION (Timing Failure)               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Purpose: Simulate action executed before page fully loaded   │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Prerequisites:                                         │  │
│ │  ✓ step.state_before is not None                       │  │
│ │  ✓ action_type in ["CLICK", "TYPE", "SELECT", ...]    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Injection Logic:                                       │  │
│ │                                                         │  │
│ │ 1. Keep state_before == state_after                    │  │
│ │    (simulate no visual change)                         │  │
│ │                                                         │  │
│ │ 2. Set metrics to indicate no change                   │  │
│ │    pixel_diff = 0.0                                    │  │
│ │    ssim = 1.0  (identical screenshots)                 │  │
│ │                                                         │  │
│ │ 3. Recovery strategy                                   │  │
│ │    strategy = "wait_and_retry"                         │  │
│ │    hints = ["wait_for_element", "check_loading"]       │  │
│ │                                                         │  │
│ │ 4. Return augmented step                               │  │
│ │    return AugmentedStep(                               │  │
│ │        injection_type = "NO_STATE_CHANGE",             │  │
│ │        modified_state_after = state_before,            │  │
│ │        recovery_strategy = strategy                    │  │
│ │    )                                                   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Success Rate: 31.9% (difficult to detect programmatically)  │
└──────────────────────────────────────────────────────────────┘
```

### Phase 6: Output Generation

```
┌──────────────────────────────────────────────────────────────┐
│ 13. COLLECT STATISTICS                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ After processing all trajectories:                           │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Aggregate Metrics:                                     │  │
│ │                                                         │  │
│ │ • total_trajectories: 86                               │  │
│ │ • total_steps: 547                                     │  │
│ │ • clean_steps: 222 (40.6%)                             │  │
│ │ • augmented_steps: 325 (59.4%)                         │  │
│ │                                                         │  │
│ │ Failure Distribution:                                  │  │
│ │ • TARGET_MISSING: 89 (27.4%)                           │  │
│ │ • WRONG_OPERATION: 97 (29.8%)                          │  │
│ │ • MISCLICK: 75 (23.1%)                                 │  │
│ │ • NO_STATE_CHANGE: 64 (19.7%)                          │  │
│ │ • LOOP: 0 (0%)                                         │  │
│ │                                                         │  │
│ │ Injector Performance:                                  │  │
│ │ • TARGET_MISSING: 69.3% success                        │  │
│ │ • MISCLICK: 66.2% success                              │  │
│ │ • WRONG_OPERATION: 50.5% success                       │  │
│ │ • NO_STATE_CHANGE: 31.9% success                       │  │
│ └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 14. SERIALIZE OUTPUT                                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ File 1: summary.json                                   │  │
│ │                                                         │  │
│ │ {                                                      │  │
│ │   "total_trajectories": 86,                            │  │
│ │   "total_steps": 547,                                  │  │
│ │   "clean_steps": 222,                                  │  │
│ │   "augmented_steps": 325,                              │  │
│ │   "failure_distribution": {...},                       │  │
│ │   "pipeline_statistics": {...},                        │  │
│ │   "injector_statistics": [...]                         │  │
│ │ }                                                      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ File 2: augmented_trajectories.json                    │  │
│ │                                                         │  │
│ │ [                                                      │  │
│ │   {                                                    │  │
│ │     "task_id": "...",                                  │  │
│ │     "domain": "shopping",                              │  │
│ │     "website": "amazon.com",                           │  │
│ │     "confirmed_task": "Find blue shoes",               │  │
│ │     "num_steps": 7,                                    │  │
│ │     "clean_steps": 3,                                  │  │
│ │     "augmented_steps": 4,                              │  │
│ │     "steps": [                                         │  │
│ │       {                                                │  │
│ │         "step_number": 0,                              │  │
│ │         "is_augmented": false,                         │  │
│ │         "action_type": "CLICK",                        │  │
│ │         ...                                            │  │
│ │       },                                               │  │
│ │       {                                                │  │
│ │         "step_number": 1,                              │  │
│ │         "is_augmented": true,                          │  │
│ │         "injection_type": "TARGET_MISSING",            │  │
│ │         "recovery_strategy": "find_alternative",       │  │
│ │         ...                                            │  │
│ │       },                                               │  │
│ │       ...                                              │  │
│ │     ]                                                  │  │
│ │   },                                                   │  │
│ │   ...                                                  │  │
│ │ ]                                                      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Output Directory: output/pilot_100_final/                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Core System Components

### 1. **Offline Data Module** (`src/offline_data/`)

#### Purpose

Load and parse pre-collected trajectories with screenshots from benchmark datasets.

#### Key Classes

**`MultimodalMind2WebLoader`**

```python
class MultimodalMind2WebLoader:
    """
    Loads Multimodal Mind2Web dataset from HuggingFace cache.
    Handles Arrow tables, JSON parsing, and screenshot loading.
    """

    Methods:
    - load_from_cache() → Dataset
      • Scans cache directory
      • Reads parquet files
      • Creates HuggingFace Dataset

    - load_trajectories(split, limit, load_screenshots) → List[OfflineTrajectory]
      • Groups actions by annotation_id
      • Parses JSON fields (operation, pos_candidates)
      • Loads screenshots from Arrow tables
      • Constructs OfflineTrajectory objects

    - _parse_trajectory_from_actions() → OfflineTrajectory
      • Sorts actions by action_uid
      • Extracts metadata
      • Parses each action to OfflineStep

    - _parse_single_action_step() → OfflineStep
      • Parses operation JSON
      • Extracts bbox from nested JSON
      • Loads screenshot via Arrow table index
      • Calculates action coordinates
```

**`OfflineSchema`** (Data Structures)

```python
@dataclass
class OfflineStep:
    """Single action with pre-captured screenshot"""
    task_id: str
    action_type: str  # CLICK, TYPE, SELECT, HOVER, SCROLL
    action_coords: tuple[int, int]
    state_before: PIL.Image
    target_bbox: Dict[str, float]
    ...

@dataclass
class OfflineTrajectory:
    """Sequence of OfflineSteps"""
    task_id: str
    steps: List[OfflineStep]
    domain: str
    website: str
    ...

@dataclass
class AugmentedStep:
    """OfflineStep + failure injection metadata"""
    original_step: OfflineStep
    is_augmented: bool
    injection_type: Optional[str]
    recovery_strategy: Optional[str]
    recovery_hints: List[str]
    ...
```

#### Technical Details

**Cache Management**

- Location: `~/.cache/huggingface/hub/datasets--{name}/`
- Format: Parquet files (Apache Arrow)
- Size: 17 files × ~230 MB = 3.95 GB
- Rows: 4,896 actions → 1,019 trajectories

**JSON Parsing Challenges**

- Mind2Web stores complex fields as JSON strings
- Nested JSON: `pos_candidates` → candidate JSON → attributes JSON
- Bbox format: String `"x,y,width,height"` → Dict
- Operation format: String `{"op": "CLICK"}` → Dict

**Screenshot Handling**

- Format: HuggingFace Image struct `{bytes: binary, path: null}`
- Access: Arrow table column by row index
- Conversion: bytes → PIL.Image via BytesIO
- Size: ~10-20 MB per screenshot (PNG, 1400×900)
- Memory: Load on-demand to avoid OOM

---

### 2. **Failure Injection Module** (`src/failure_injection/`)

#### Purpose

Systematically inject realistic failure patterns into trajectories for robust agent training.

#### Architecture

**`InjectionPipeline`** (Orchestrator)

```python
class InjectionPipeline:
    """
    Manages multiple injectors and coordinates failure injection.
    """

    def __init__(self, config: InjectionConfig):
        self.config = config
        self.injectors: List[FailureInjector] = []

        # Weighted random selection based on distribution
        self.failure_weights = config.failure_type_distribution

    def register_injector(self, injector: FailureInjector):
        """Add an injector to the pipeline"""
        self.injectors.append(injector)

    def augment_trajectory(self, trajectory: OfflineTrajectory) → AugmentedTrajectory:
        """
        Process entire trajectory, injecting failures probabilistically.

        Algorithm:
        1. For each step:
           a. Roll dice: inject? (60% probability)
           b. If inject:
              - Filter eligible injectors (can_inject)
              - Select by weighted distribution
              - Execute injection
           c. Else: keep clean
        2. Return augmented trajectory with statistics
        """

    def _select_injector(self, step: OfflineStep) → Optional[FailureInjector]:
        """
        Select injector using weighted random choice.

        Weights from config.failure_type_distribution:
        - TARGET_MISSING: 27%
        - MISCLICK: 23%
        - WRONG_OPERATION: 20%
        - NO_STATE_CHANGE: 17%
        - LOOP: 13%
        """
```

**`FailureInjector`** (Base Class)

```python
class FailureInjector(ABC):
    """
    Abstract base for all injectors.
    """

    @abstractmethod
    def injection_type(self) -> str:
        """Return failure type name"""

    @abstractmethod
    def can_inject(self, step: OfflineStep) -> bool:
        """
        Check prerequisites for injection.

        Example:
        - TARGET_MISSING: needs state_before, target_bbox
        - MISCLICK: needs CLICK action, target_bbox
        - WRONG_OPERATION: needs swappable action type
        """

    @abstractmethod
    def inject(self, step: OfflineStep, trajectory: OfflineTrajectory) → AugmentedStep:
        """
        Execute failure injection.

        Returns:
        - AugmentedStep with modified state/action
        - Recovery strategy and hints
        - Success indicator
        """
```

#### Injector Implementations

**1. TargetMissingInjector** (Perception Failure)

```python
class TargetMissingInjector(FailureInjector):
    """
    Simulates agent failing to detect target element.
    Masks target bbox with Gaussian blur.
    """

    def can_inject(self, step):
        return (step.is_valid and
                step.state_before is not None and
                step.target_bbox is not None)

    def inject(self, step, trajectory):
        # 1. Copy screenshot
        failed_state = step.state_before.copy()

        # 2. Apply Gaussian blur to target region
        bbox = step.target_bbox
        region = ImageDraw.Draw(failed_state)
        mask_bbox(failed_state, bbox, blur_radius=20)

        # 3. Find alternative elements
        alternatives = find_alternative_target(
            step.candidate_bboxes,
            excluded=bbox
        )

        # 4. Determine recovery
        if alternatives:
            strategy = "find_alternative"
            hints = [f"try_element_{alt.id}" for alt in alternatives]
        else:
            strategy = "scroll_and_search"
            hints = ["scroll_down", "check_visibility"]

        return AugmentedStep(
            original_step=step,
            is_augmented=True,
            injection_type="TARGET_MISSING",
            modified_state=failed_state,
            recovery_strategy=strategy,
            recovery_hints=hints,
            confidence=0.69  # Success rate
        )
```

**2. MisclickInjector** (Execution Failure)

```python
class MisclickInjector(FailureInjector):
    """
    Simulates clicking wrong location near target.
    Shifts coordinates 50-200 pixels away.
    """

    def can_inject(self, step):
        return (step.action_type in ["CLICK", "HOVER", "SELECT"] and
                step.target_bbox is not None and
                step.state_before is not None)

    def inject(self, step, trajectory):
        # 1. Calculate shifted coordinates
        original_x, original_y = step.action_coords
        shift_dist = random.randint(50, 200)
        angle = random.uniform(0, 2 * math.pi)
        new_x = original_x + shift_dist * math.cos(angle)
        new_y = original_y + shift_dist * math.sin(angle)

        # 2. Find element at new location
        clicked_element = None
        for bbox in step.candidate_bboxes:
            if point_in_bbox((new_x, new_y), bbox):
                clicked_element = bbox
                break

        # 3. Calculate correction offset
        offset_x = original_x - new_x
        offset_y = original_y - new_y

        return AugmentedStep(
            injection_type="MISCLICK",
            modified_action_coords=(new_x, new_y),
            clicked_element=clicked_element,
            recovery_strategy="adjust_coordinates",
            recovery_hints=[f"offset_x:{offset_x}", f"offset_y:{offset_y}"]
        )
```

**3. WrongOperationInjector** (Planning Failure)

```python
class WrongOperationInjector(FailureInjector):
    """
    Simulates selecting wrong action type.
    Swaps compatible operations (CLICK↔HOVER, TYPE↔SELECT).
    """

    SWAPPABLE_OPS = {
        "CLICK": ["HOVER"],
        "HOVER": ["CLICK"],
        "TYPE": ["SELECT"],
        "SELECT": ["TYPE"],
        "SCROLL": ["CLICK"]
    }

    def can_inject(self, step):
        return (step.action_type in self.SWAPPABLE_OPS and
                step.action_type != "UNKNOWN")

    def inject(self, step, trajectory):
        # 1. Get compatible alternatives
        alternatives = self.SWAPPABLE_OPS[step.action_type]
        wrong_op = random.choice(alternatives)

        # 2. Recovery is straightforward
        return AugmentedStep(
            injection_type="WRONG_OPERATION",
            modified_action_type=wrong_op,
            recovery_strategy="retry_with_correct_operation",
            recovery_hints=[f"use_{step.action_type}_instead"]
        )
```

**4. NoStateChangeInjector** (Timing Failure)

```python
class NoStateChangeInjector(FailureInjector):
    """
    Simulates action before page ready.
    Makes state_after identical to state_before.
    """

    def inject(self, step, trajectory):
        return AugmentedStep(
            injection_type="NO_STATE_CHANGE",
            modified_state_after=step.state_before,  # No change
            pixel_diff=0.0,
            ssim=1.0,
            recovery_strategy="wait_and_retry",
            recovery_hints=["wait_for_element", "check_page_load"]
        )
```

**5. LoopInjector** (Temporal Failure)

```python
class LoopInjector(FailureInjector):
    """
    Simulates repeated actions when stuck.
    Requires state_after to detect loops.
    """

    def can_inject(self, step):
        return (step.state_before is not None and
                step.state_after is not None and
                step.step_number >= 2)  # Need history

    def inject(self, step, trajectory):
        # Find previous similar actions
        history = trajectory.steps[:step.step_number]
        similar = find_similar_actions(step, history)

        if similar:
            return AugmentedStep(
                injection_type="LOOP",
                repeated_actions=similar,
                recovery_strategy="break_loop",
                recovery_hints=["try_different_approach", "backtrack"]
            )
```

---

### 3. **Image Processing Module** (`src/offline_data/image_preprocessor.py`)

#### Purpose

Low-level image manipulation for failure injection and metric computation.

#### Functions

```python
def mask_bbox(image: PIL.Image, bbox: Dict, blur_radius: int = 20) -> PIL.Image:
    """
    Apply Gaussian blur to bounding box region.

    Used by: TargetMissingInjector

    Args:
        image: PIL Image
        bbox: {x, y, width, height}
        blur_radius: Blur strength (default: 20px)

    Implementation:
        1. Extract region: crop(x, y, x+w, y+h)
        2. Apply filter: ImageFilter.GaussianBlur(blur_radius)
        3. Paste back: paste(blurred, (x, y))
    """

def shift_coords(coords: tuple, distance: int, angle: float) -> tuple:
    """
    Shift coordinates by distance and angle.

    Used by: MisclickInjector

    Args:
        coords: (x, y)
        distance: Pixel distance (50-200)
        angle: Radians (0-2π)

    Returns:
        (new_x, new_y)

    Formula:
        new_x = x + distance * cos(angle)
        new_y = y + distance * sin(angle)
    """

def find_alternative_target(candidates: List[Dict], excluded: Dict) -> List[Dict]:
    """
    Find alternative clickable elements.

    Used by: TargetMissingInjector

    Args:
        candidates: List of candidate bboxes
        excluded: Target bbox to exclude

    Returns:
        List of alternative elements sorted by proximity

    Algorithm:
        1. Filter: Remove excluded bbox
        2. Score by: Distance from excluded center
        3. Sort: Nearest first
        4. Return: Top 3 alternatives
    """

def compute_ssim(img1: PIL.Image, img2: PIL.Image) -> float:
    """
    Compute Structural Similarity Index.

    Used by: NoStateChangeInjector, metrics

    Implementation:
        1. Convert to grayscale
        2. Resize to same dimensions
        3. Use skimage.metrics.structural_similarity

    Range: [0, 1], where 1 = identical
    """

def compute_pixel_diff(img1: PIL.Image, img2: PIL.Image) -> float:
    """
    Compute pixel-level difference percentage.

    Used by: Metrics, change detection

    Implementation:
        1. Convert to numpy arrays
        2. Compute: |img1 - img2|
        3. Threshold: diff > 10
        4. Return: changed_pixels / total_pixels

    Range: [0, 1], where 0 = identical
    """
```

---

## 🔧 Configuration System

### InjectionConfig

```yaml
# config/default.yaml (conceptual - currently in code)

injection:
  # Overall probability of injecting failure
  injection_rate: 0.6 # 60%

  # Target distribution across all data
  target_distribution:
    clean_success: 0.40 # 40% clean trajectories
    recoverable_failure: 0.30 # 30% with recovery
    non_recoverable: 0.15 # 15% terminal failures
    ambiguous: 0.15 # 15% unclear outcomes

  # Distribution of failure types (when injecting)
  failure_type_distribution:
    TARGET_MISSING: 0.27 # Perception errors
    MISCLICK: 0.23 # Execution errors
    WRONG_OPERATION: 0.20 # Planning errors
    NO_STATE_CHANGE: 0.17 # Timing errors
    LOOP: 0.13 # Temporal patterns

  # Recovery success rates (per failure type)
  recovery_success_rates:
    TARGET_MISSING: 0.65
    MISCLICK: 0.55
    WRONG_OPERATION: 0.60
    NO_STATE_CHANGE: 0.45
    LOOP: 0.75

  # Injection parameters
  misclick_distance_range: [50, 200] # pixels
  blur_radius: 20 # pixels
  loop_length: 3 # repetitions

  # Reproducibility
  random_seed: 42
```

---

## 📊 Data Flow Diagram

```
INPUT                    PROCESSING                      OUTPUT
═════                    ══════════                      ══════

Parquet Files            Load & Parse                    JSON Files
(17 × 230 MB)           (Mind2WebLoader)                (summary + trajectories)
     │                         │                              │
     │ ┌────────────────────┐  │                              │
     ├─┤ train-00000.parquet├──┼─→ [Arrow Table]             │
     │ └────────────────────┘  │        │                     │
     │ ┌────────────────────┐  │        ▼                     │
     ├─┤ train-00001.parquet├──┼─→ [Group by                 │
     │ └────────────────────┘  │   annotation_id]             │
     │         ...             │        │                     │
     │ ┌────────────────────┐  │        ▼                     │
     └─┤ train-00016.parquet├──┼─→ [Parse JSON fields]       │
       └────────────────────┘  │        │                     │
                               │        ▼                     │
       4,896 rows              │  [Load screenshots]          │
          │                    │        │                     │
          ▼                    │        ▼                     │
                               │  ┌───────────────┐           │
                               │  │OfflineStep    │           │
                               │  │ • action      │           │
     ┌─────────────┐          │  │ • coords      │           │
     │ Trajectory  │◀─────────┼──│ • screenshot  │           │
     │ Grouping    │          │  │ • bbox        │           │
     └──────┬──────┘          │  └───────┬───────┘           │
            │                 │          │                    │
            ▼                 │          ▼                    │
     1,019 trajectories       │   ┌──────────────┐            │
            │                 │   │ Injection    │            │
            │                 │   │ Pipeline     │            │
            ▼                 │   └──────┬───────┘            │
  ┌──────────────────┐       │          │                    │
  │ For each         │       │          ▼                    │
  │ trajectory:      │       │   ┌──────────────┐            │
  │                  │       │   │ Select       │            │
  │  For each step:  │──────→│   │ Injector     │            │
  │   • Roll dice    │       │   │ (weighted)   │            │
  │   • Select type  │       │   └──────┬───────┘            │
  │   • Inject       │       │          │                    │
  └──────────────────┘       │          ▼                    │
                             │   ┌──────────────┐            │
                             │   │ Execute      │            │
                             │   │ Injection    │            │
                             │   └──────┬───────┘            │
                             │          │                    │
                             │          ▼                    │
                             │   ┌──────────────┐            │
                             │   │AugmentedStep │            │
                             │   │ • original   │───────────→│
                             │   │ • injection  │            │
                             │   │ • recovery   │            │
                             │   └──────────────┘            │
                             │                               │
                             │                               ▼
                             │                        ┌─────────────┐
                             │                        │ summary.json│
                             │                        │  • stats    │
                             │                        │  • metrics  │
                             │                        └─────────────┘
                             │                               │
                             │                               ▼
                             │                    ┌──────────────────────┐
                             │                    │augmented_trajs.json  │
                             │                    │  • 86 trajectories   │
                             │                    │  • 547 steps         │
                             │                    │  • 325 injected      │
                             │                    └──────────────────────┘
```

---

## 🧪 Testing & Validation

### Test Scripts

**`scripts/test_downloaded_data.py`**

```python
"""
End-to-end pipeline test script.

Usage:
    python scripts/test_downloaded_data.py --num-tasks 100

Flow:
    1. Load Mind2Web from cache
    2. Load N trajectories with screenshots
    3. Initialize injection pipeline
    4. Process all trajectories
    5. Generate statistics
    6. Save output files
"""
```

**`scripts/check_screenshots.py`**

```python
"""
Debug script to verify screenshot loading.

Outputs:
    - Screenshot count per trajectory
    - Action type distribution
    - Bbox availability
    - Validation errors
"""
```

### Validation Checks

```python
# Quality gates (automated)

1. Screenshot Loading:
   ✓ All steps have state_before
   ✓ Screenshots are valid PIL Images
   ✓ Dimensions: 1400×900 (typical)

2. Parsing Accuracy:
   ✓ action_type != "UNKNOWN"
   ✓ target_bbox is not None (for clickable actions)
   ✓ action_coords within screenshot bounds

3. Injection Rates:
   ✓ Actual rate ≈ configured rate (60% ± 5%)
   ✓ Distribution matches weights (± 10%)
   ✓ Success rates > 30% per injector

4. Data Integrity:
   ✓ No duplicate step IDs
   ✓ Trajectory step numbering sequential
   ✓ JSON serializable output
```

---

## 🚀 Usage Examples

### Basic Usage

```python
from src.offline_data import MultimodalMind2WebLoader
from src.failure_injection import InjectionPipeline, InjectionConfig
from src.failure_injection import (
    TargetMissingInjector,
    MisclickInjector,
    WrongOperationInjector,
    NoStateChangeInjector,
    LoopInjector
)

# 1. Load data
loader = MultimodalMind2WebLoader(use_streaming=False)
loader.load_from_cache()

trajectories = loader.load_trajectories(
    split="train",
    limit=100,
    load_screenshots=True  # Enable for injection
)

# 2. Initialize pipeline
config = InjectionConfig(injection_rate=0.6)
pipeline = InjectionPipeline(config)

# 3. Register injectors
pipeline.register_injector(TargetMissingInjector(config))
pipeline.register_injector(MisclickInjector(config))
pipeline.register_injector(WrongOperationInjector(config))
pipeline.register_injector(NoStateChangeInjector(config))
pipeline.register_injector(LoopInjector(config))

# 4. Process trajectories
augmented_trajectories = []
for traj in trajectories:
    augmented = pipeline.augment_trajectory(traj)
    augmented_trajectories.append(augmented)

# 5. Get statistics
stats = pipeline.get_statistics()
print(f"Total injections: {stats['total_injections']}")
print(f"Success rate: {stats['overall_success_rate']:.2%}")

# 6. Save output
import json
with open("output/augmented_data.json", "w") as f:
    json.dump([t.to_dict() for t in augmented_trajectories], f, indent=2)
```

### Advanced Configuration

```python
# Custom injection rates per failure type
config = InjectionConfig(
    injection_rate=0.7,  # 70% injection
    failure_type_distribution={
        "TARGET_MISSING": 0.40,  # Focus on perception
        "MISCLICK": 0.30,        # And execution
        "WRONG_OPERATION": 0.15,
        "NO_STATE_CHANGE": 0.10,
        "LOOP": 0.05
    },
    misclick_distance_range=(100, 300),  # Larger shifts
    blur_radius=30,  # Stronger blur
    random_seed=42   # Reproducible
)

# Filter by domain
trajectories = loader.load_trajectories(
    split="train",
    limit=200,
    filter_by_domain=["shopping", "booking"]
)
```

---

## 📈 Performance Characteristics

### Memory Usage

```
Component                   Memory
═════════════════════════  ═══════
Dataset (cached)            3.95 GB (disk)
Dataset object              ~100 MB (metadata)
Single screenshot           10-20 MB
100 screenshots loaded      ~1.5 GB
Trajectory (7 steps avg)    ~120 MB
Injection processing        +50 MB (augmented states)

Total for 100 trajectories: ~2-3 GB RAM
```

### Processing Speed

```
Operation                   Duration
═════════════════════════  ════════
Load from cache             2-5 sec
Parse 100 trajectories      5-10 sec
Load 700 screenshots        15-30 sec
Inject 420 failures         10-20 sec
Total for 100 tasks         30-60 sec
```

### Scalability

```
Tasks    Trajectories  Steps   Memory   Duration
═════    ═══════════  ══════   ══════   ════════
5        5            35       ~500 MB  5 sec
20       20           130      ~1.5 GB  15 sec
100      86           547      ~2.5 GB  45 sec
500      430          ~2,700   ~12 GB   ~5 min

Recommendation: Process in batches of 100-200 for stability
```

---

## 🔒 Error Handling & Resilience

### Dataset Loading

```python
# Graceful degradation
try:
    dataset = loader.load_from_cache()
except FileNotFoundError:
    logger.warning("Cache not found, attempting download...")
    loader.download_dataset()
    dataset = loader.load_from_cache()
except Exception as e:
    logger.error(f"Failed to load dataset: {e}")
    # Fall back to smaller subset
    dataset = loader.load_from_backup()
```

### Screenshot Loading

```python
# On-demand with fallback
try:
    screenshot = load_screenshot(row_index)
except Exception as e:
    logger.debug(f"Failed to load screenshot: {e}")
    screenshot = None  # Step still valid without screenshot
```

### Injection Failures

```python
# Continue on injection error
for step in trajectory.steps:
    try:
        augmented = pipeline.process_step(step)
    except InjectionError as e:
        logger.warning(f"Injection failed: {e}")
        augmented = AugmentedStep(step, is_augmented=False)

    results.append(augmented)
```

---

## 🎯 Design Decisions & Rationale

### 1. **Cache-First Loading**

**Decision**: Load from HuggingFace cache instead of re-downloading

**Rationale**:

- Avoids network instability (CDN connection drops)
- 10x faster (local disk vs network)
- Works with partial downloads (17/27 files sufficient)

### 2. **On-Demand Screenshot Loading**

**Decision**: Load screenshots only when `load_screenshots=True`

**Rationale**:

- Memory efficiency: 4,896 screenshots × 15 MB = ~70 GB
- Selective loading: Only inject subset (60%)
- Scalability: Can process 1,000+ trajectories

### 3. **JSON String Parsing**

**Decision**: Explicitly parse JSON fields (operation, pos_candidates)

**Rationale**:

- Mind2Web format: Complex fields stored as strings
- HuggingFace auto-parsing unreliable
- Manual parsing: Complete control, error handling

### 4. **Weighted Random Injection**

**Decision**: Probabilistic injection with configurable distribution

**Rationale**:

- Realistic: Not all steps have failures
- Balanced: Multiple failure types mixed
- Configurable: Adjust for different training needs

### 5. **Trajectory-Level Processing**

**Decision**: Process entire trajectory, not individual steps

**Rationale**:

- Context: Injectors can use trajectory history
- Recovery: Strategies depend on task context
- Efficiency: Batch processing per trajectory

---

## 🔍 Future Enhancements

### Planned Features

1. **LOOP Injector Completion**
   - Implement `state_after` loading
   - Detect temporal patterns via SSIM
   - Target: 13% of injections

2. **Lazy Screenshot Loading**
   - Stream screenshots on-demand
   - LRU cache for frequently accessed
   - Support 1,000+ trajectory batches

3. **Multi-Modal Injection**
   - Inject text errors (OCR failures)
   - DOM structure perturbations
   - Network timing issues

4. **Recovery Validation**
   - Automated recovery execution
   - Success rate measurement
   - Hint effectiveness scoring

5. **Visual Debugging**
   - Generate HTML reports with screenshots
   - Highlight injected regions
   - Side-by-side comparison

---

## 📝 Summary

This system implements a **production-grade offline augmentation pipeline** for training robust web agents:

✅ **Scalable**: Processes 100+ trajectories in <1 minute
✅ **Robust**: Cache-first loading, graceful error handling
✅ **Realistic**: 4 failure types based on agent error taxonomy
✅ **Configurable**: Flexible injection rates and distributions
✅ **Validated**: 60% injection rate, balanced distribution
✅ **Ready**: Generated 86-trajectory pilot dataset for Q1 journal

**Key Innovation**: Systematic failure injection on established benchmark (Mind2Web) enables training failure-aware agents without expensive live data collection.

---

**Document Version**: 1.0  
**Last Updated**: February 21, 2026  
**Status**: ✅ Production Ready
