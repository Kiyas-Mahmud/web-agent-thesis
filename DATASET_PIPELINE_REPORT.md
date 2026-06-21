# Dataset Pipeline Report — `dataset_70k_safe`

**Author:** Kiyas Mahmud · **Branch:** Dataset · **Final size:** 70,965 records / 10,110 trajectories

---

## 1. Executive Summary

The `dataset_70k_safe` corpus is a **70,965-step web-agent failure dataset**
built from Multimodal Mind2Web. Production happens in two phases:

1. **Generation** — `generate_70k_safe.py` loads ~14k clean Mind2Web steps,
   applies five augmentation passes that inject four failure types
   (TARGET_MISSING, MISCLICK, WRONG_OPERATION, LOOP), and renders 256 px
   screenshots for `state_before` / `state_after`. Output:
   `augmented_trajectories.json`.
2. **Post-processing** — Four sequential scripts enrich the schema, repair
   broken image paths without dropping records, normalise paths /
   descriptions, and split the data into `train` / `val` / `test` by
   `original_task_id` to prevent trajectory leakage.

The final canonical training file is
[`FINAL_Trajectories_Update.json`](output/dataset_70k_safe/FINAL_Trajectories_Update.json)
with companion split files
[`split_train.json`](output/dataset_70k_safe/split_train.json) (38,875),
[`split_val.json`](output/dataset_70k_safe/split_val.json) (16,070),
[`split_test.json`](output/dataset_70k_safe/split_test.json) (16,020).

---

## 2. Pipeline Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1 — GENERATION                             │
└──────────────────────────────────────────────────────────────────────────┘

   Multimodal Mind2Web (HuggingFace cache: dataset/mind2web_offline/)
                              │
                              │   loaded by  src/offline_data/mind2web_loader.py
                              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  generate_70k_safe.py                                            │
   │   • 4 splits × 5 passes (pass1..pass5, seeds 42/100/200/300/400) │
   │   • InjectionPipeline from src/failure_injection/                │
   │   • 256 px / 60% JPEG, batch=5 trajectories (memory-safe)        │
   │   • progress/  → resumable per-split, per-pass checkpoints       │
   └──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        output/dataset_70k_safe/augmented_trajectories.json   (70,965 raw)
        output/dataset_70k_safe/images/   (131,721 JPEGs in 10,111 folders)


┌──────────────────────────────────────────────────────────────────────────┐
│                       PHASE 2 — POST-PROCESSING                          │
└──────────────────────────────────────────────────────────────────────────┘

   augmented_trajectories.json
                              │
                              │  prepare_actual.py
                              │  (schema enrichment: 17 spec fields,
                              │   failure_type / recovery_strategy mapping,
                              │   visual_diff & confidence heuristics)
                              ▼
   augmented_trajectories_READY.json
                              │
                              │  repair_image_paths.py
                              │  (3 strategies: find-on-disk → borrow neighbour
                              │   → grey placeholder; never removes records)
                              ▼
   augmented_trajectories_READY_REPAIRED.json
                              │
                              │  apply_final_fixes.py
                              │  (Fix 1: \ → /     paths)
                              │  (Fix 2: element_N → semantic action_target_desc)
                              │  (Fix 3: borrowed_image=false where missing)
                              ▼
   FINAL_Trajectories_Update.json   ← canonical 70,965-step file
                              │
                              │  split_dataset.py
                              │  (group by original_task_id, hard split-field
                              │   rule, random.seed(42), no leakage)
                              ▼
   ┌──────────────────────┬──────────────────────┬──────────────────────┐
   │   split_train.json   │    split_val.json    │   split_test.json    │
   │     38,875 recs      │      16,070 recs     │      16,020 recs     │
   │     1,009 task_ids   │       506 task_ids   │       507 task_ids   │
   └──────────────────────┴──────────────────────┴──────────────────────┘
```

---

## 3. Phase 1 — Generation

### 3.1 Main producer
**File:** [`generate_70k_safe.py`](generate_70k_safe.py)

| Aspect | Value |
|---|---|
| Inputs | Mind2Web cache (HuggingFace) |
| Outputs | `output/dataset_70k_safe/augmented_trajectories.json` + `images/` + `progress/` |
| Configuration | `BATCH_SIZE=5` · `IMAGE_WIDTH=256 px` · `IMAGE_QUALITY=60%` |
| Splits processed | `train`, `test_domain`, `test_task`, `test_website` |
| Augmentation passes | 5 passes with seeds 42 / 100 / 200 / 300 / 400 |
| Skipped injectors | `NoStateChangeInjector` (memory-intensive) |

**Why this script** — earlier variants (`generate_70k_batch.py`,
`generate_70k_dataset.py`, `generate_70k_light.py`,
`generate_70k_multipass.py`) were prototypes. Only `generate_70k_safe.py`
included the memory-safety controls (small batches, reduced image size,
per-split processing, resumable checkpoints) needed to complete the run on
a single workstation. Evidence: `progress/` directory contains 40 files
(`<split>_pass<1..5>_steps.json` and `_stats.json`) only for this script.

### 3.2 Source modules used by the generator
All under `src/`:

| Module | Role |
|---|---|
| [`src/offline_data/mind2web_loader.py`](src/offline_data/mind2web_loader.py) | `MultimodalMind2WebLoader` — loads Mind2Web trajectories from HuggingFace cache |
| [`src/offline_data/offline_schema.py`](src/offline_data/offline_schema.py) | `OfflineStep`, `OfflineTrajectory`, `AugmentedStep` data classes |
| [`src/failure_injection/injection_engine.py`](src/failure_injection/injection_engine.py) | `InjectionPipeline` orchestrator + `InjectionConfig` |
| [`src/failure_injection/target_missing.py`](src/failure_injection/target_missing.py) | Hides target element → produces PERCEPTION_ERROR |
| [`src/failure_injection/misclick.py`](src/failure_injection/misclick.py) | Clicks adjacent wrong element → ACTION_MISMATCH |
| [`src/failure_injection/wrong_operation.py`](src/failure_injection/wrong_operation.py) | Replaces correct action verb → ACTION_MISMATCH |
| [`src/failure_injection/loop.py`](src/failure_injection/loop.py) | Repeats prior state → LOOP_DETECTED |
| [`config/default.yaml`](config/default.yaml) | Global config: viewport, dataset targets, metric thresholds |

### 3.3 Failure distribution after Phase 1
| Failure / outcome | Count | % |
|---|---:|---:|
| Clean (no injection) | 19,929 | 28.08% |
| TARGET_MISSING → PERCEPTION_ERROR | 18,043 | 25.43% |
| WRONG_OPERATION → ACTION_MISMATCH | 15,268 | 21.51% |
| MISCLICK → ACTION_MISMATCH | 12,470 | 17.57% |
| LOOP → LOOP_DETECTED | 5,255 | 7.41% |

---

## 4. Phase 2 — Post-processing

Four sequential scripts. Each preserves record count (no records removed).

### Step 2.1 — Schema enrichment
**File:** [`prepare_actual.py`](prepare_actual.py)

- Reads: `augmented_trajectories.json`
- Writes: `augmented_trajectories_READY.json`
- Adds the 17 spec fields the trainer expects.
- Maps `injection_type` → `failure_type`:
  `TARGET_MISSING → PERCEPTION_ERROR`,
  `MISCLICK / WRONG_OPERATION → ACTION_MISMATCH`,
  `LOOP → LOOP_DETECTED`,
  `None → NONE`.
- Maps `recovery_action` → `recovery_strategy`
  (RETRY / REPLAN / BACKTRACK / ALTERNATIVE_TARGET / ABORT / NONE).
- Computes `visual_diff_score`, `agent_confidence_before`,
  `failure_confidence` heuristically from `action_type` and `is_augmented`.
- Sets `execution_outcome = FAILURE` for augmented rows, else `SUCCESS`.

### Step 2.2 — Image-path repair
**File:** [`repair_image_paths.py`](repair_image_paths.py)

- Reads: `augmented_trajectories_READY.json`
- Writes: `augmented_trajectories_READY_REPAIRED.json`
- Three strategies, applied in order, never removes records:
  1. **Find on disk** — search `images/<task_id>/step_NNNN_<side>.jpg`
     under several name patterns. If found, fill the path.
  2. **Borrow** — use the neighbour-step image from the same trajectory
     (state_after of step N − 1 ≡ state_before of step N). Flag with
     `borrowed_image: true`.
  3. **Placeholder** — generate a 256 × 256 grey JPEG with text
     "missing screenshot". Flag with `placeholder_image: true`.
- Result on this dataset: 0 found-on-disk, 10,210 borrowed, 0 placeholder.
  (10,110 of the 10,210 are last-step `state_after` frames the pipeline
  never captured because the trajectory ended.)

### Step 2.3 — Three deterministic fixes
**File:** [`apply_final_fixes.py`](apply_final_fixes.py)

- Reads: `augmented_trajectories_READY_REPAIRED.json`
- Writes: `FINAL_Trajectories_Update.json`  ← **canonical training file**
- **Fix 1** — Replace `\` with `/` in `state_before` / `state_after`
  (Windows → Unix path style). 141,930 paths normalised (70,965 × 2).
- **Fix 2** — Replace generic `element_N` values in `action_target_desc`
  with semantic labels using `action_type` + `bbox` heuristics:
  - `TYPE` → `"text input field"`
  - `SELECT` → `"dropdown selector"`
  - `CLICK` & w > 200 & h > 40 → `"large button or link"`
  - `CLICK` & w < 50 & h < 50 → `"small icon or checkbox"`
  - other `CLICK` → `"clickable element at (X, Y)"`
- **Fix 3** — Add `borrowed_image: false` to records that lack the field
  (60,775 records); preserve `borrowed_image: true` on the other 10,190.

### Step 2.4 — Train / val / test split
**File:** [`split_dataset.py`](split_dataset.py)

- Reads: `FINAL_Trajectories_Update.json`
- Writes: `split_train.json`, `split_val.json`, `split_test.json`
- Groups records by `original_task_id` so a trajectory never spans splits.
- Hard rule: `split == "train"` → train output only;
  `split` starts with `test_` → val/test output only. No mixing.
- The source `original_task_id` pool is already partitioned ~50% train /
  ~50% test_*, so the achievable ratio is **~50 / 25 / 25** at task-id
  level. The original 80/10/10 target is unreachable without trajectory
  leakage; the constraint takes precedence.
- `random.seed(42)` for reproducibility.

| Output | Records | Task IDs | Record % |
|---|---:|---:|---:|
| `split_train.json` | 38,875 | 1,009 | 54.78% |
| `split_val.json`   | 16,070 |   506 | 22.64% |
| `split_test.json`  | 16,020 |   507 | 22.57% |
| **Total**          | **70,965** | **2,022** | **100%** |

**Leakage check** — task-id overlap train ∩ val = 0, train ∩ test = 0,
val ∩ test = 0 (verified by the script after writing).

---

## 5. Quality / Validation Scripts (parallel, not in chain)

These do not transform the dataset; they audit it.

| File | Purpose |
|---|---|
| [`_quality_gates.py`](_quality_gates.py) | Four gates: error-page rate < 2%, success consistency > 95%, failure-type balance, recovery-execution rate > 80% |
| [`_audit.py`](_audit.py) | Schema-level audit of every record |
| [`_quality_gates.py`](_quality_gates.py), [`validate_10k_dataset.py`](validate_10k_dataset.py) | Programmatic validity checks |
| [`tests/`](tests/) | pytest suite |
| [`analyze_final_dataset.py`](analyze_final_dataset.py), [`generate_dataset_report.py`](generate_dataset_report.py) | Descriptive statistics for paper figures |

---

## 6. Final Dataset Layout

```
output/dataset_70k_safe/
├── augmented_trajectories.json                  raw, 70,965 (Phase 1 output)
├── augmented_trajectories_READY.json            schema-enriched
├── augmented_trajectories_READY_REPAIRED.json   image paths repaired
├── FINAL_Trajectories_Update.json               canonical 70,965  ★ trainer reads this
├── split_train.json                             38,875 records
├── split_val.json                               16,070 records
├── split_test.json                              16,020 records
├── images/                                      131,721 JPEGs / 10,111 trajectory folders
├── progress/                                    40 resumable checkpoint files
└── summary.json                                 generation metadata
```

---

## 7. Reproducing the Pipeline

From repo root, one command per stage:

```bash
# Phase 1 — generation (long-running, hours; resumable)
python generate_70k_safe.py

# Phase 2 — post-processing (fast, minutes)
python prepare_actual.py
python repair_image_paths.py output/dataset_70k_safe/augmented_trajectories_READY.json output/dataset_70k_safe/images
python apply_final_fixes.py
python split_dataset.py
```

Each step prints a verification report and asserts record count = 70,965.

---

## 8. Known Caveats (declare in the paper)

1. **Action space limited to 3 types** — only `CLICK` (83.6%), `TYPE` (12.5%),
   and `SELECT` (3.9%) are present. `SCROLL` and `NAVIGATE` from the original
   spec are absent because Mind2Web source contains no such actions.
2. **14.4% of records use a borrowed neighbour image** for `state_before` or
   `state_after` (mostly last-step screenshots the pipeline never captured).
   Add `not r.get("borrowed_image")` to the eval filter for clean visual
   metrics.
3. **`recovery_strategy`, `recovery_success`, `failure_confidence`,
   `visual_diff_score`** are heuristic labels computed in `prepare_actual.py`,
   not observed agent behaviour. They are noisy supervision targets.
4. **Train / val / test ratio is 50 / 25 / 25** at the task-id level, not the
   commonly-cited 80/10/10. The leakage-prevention constraint
   (no `original_task_id` shared across splits) and the existing
   `split` field together force this ratio.
5. **3,805 records lack `action_target_bbox`** (5.4%). `action_coordinates`
   is present for all 70,965 records, so models that need only point
   coordinates are unaffected.

---

## 9. Field Schema (FINAL_Trajectories_Update.json)

| # | Field | Type | Notes |
|---:|---|---|---|
| 1 | `task_id` | string | `<split>_<pass>_<uuid>_<step>` |
| 2 | `task_description` | string | Mind2Web task prompt |
| 3 | `website_domain` | string | `web-general` / `unseen-domain` / `seen-website` / `unseen-website` |
| 4 | `state_before` | string | path under `images/` (forward slashes) |
| 5 | `state_after` | string | same |
| 6 | `visual_diff_score` | float | 0.01–0.55 |
| 7 | `action_type` | string | CLICK · TYPE · SELECT |
| 8 | `action_target_desc` | string | semantic label (Fix 2) |
| 9 | `action_coordinates` | [x, y] | screen coordinates |
| 10 | `execution_outcome` | string | SUCCESS · FAILURE |
| 11 | `failure_type` | string | NONE · ACTION_MISMATCH · PERCEPTION_ERROR · LOOP_DETECTED |
| 12 | `failure_confidence` | float | heuristic 0–1 |
| 13 | `recovery_strategy` | string | NONE · RETRY · REPLAN · BACKTRACK · ALTERNATIVE_TARGET |
| 14 | `recovery_success` | bool | heuristic |
| 15 | `agent_confidence_before` | float | heuristic 0–1 |
| 16 | `reflection_text` | string | short text label |
| 17 | `memory_update_flag` | bool | true on augmented rows |
| 18 | `original_task_id` | string | uuid only — used for splitting |
| 19 | `split` | string | source split: train · test_domain · test_task · test_website |
| 20 | `pass` | string | pass1..pass5 |
| 21 | `is_augmented` | bool | |
| 22 | `injection_type` | string | TARGET_MISSING · MISCLICK · WRONG_OPERATION · LOOP · None |
| 23 | `action_target_bbox` | object | `{x, y, width, height}` (94.6% populated) |
| 24 | `borrowed_image` | bool | true if image is from neighbour step |

---

*Generated for thesis supervisor review. All file paths are relative to
`e:/University/thesis/datacollection/`.*
