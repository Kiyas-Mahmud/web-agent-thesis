# Gold Dataset Collection Implementation and Target

## Target

Build a leakage-safe gold evaluation dataset for the thesis model.

- First target: **2,000 collected gold samples**.
- Manual review target: **300-500 samples**.
- Timeline target: **2-3 weeks** for collection and validation after the collector is stable.
- Existing `output/dataset_70k_safe` remains useful for synthetic pretraining/debugging, but final visual-failure claims must be evaluated on this gold dataset.

## Current Decision - 2026-06-22

The synthetic 70k data is **not acceptable as final thesis gold data** because simple metadata rules can recover labels. It remains useful only for pipeline development and optional pretraining.

The cleanest current real-browser seed is:

- `logs/gold_tasks_final_v3_balanced.jsonl`
- Output: `output/gold_dataset_final_v3_balanced`
- Size: 32 tasks / 32 collected steps / 64 screenshots
- Label balance: 16 `SUCCESS`, 16 `FAILURE`
- Failure labels: 16 `NONE`, 16 `PERCEPTION_ERROR`
- Seed audit: passed
- Dataset validation: passed
- Export leakage audit: passed
- Image integrity: 64 PNG files, 1280x720, no blank-like images

This v3 dataset is a **valid protocol check and seed**, not the final publishable dataset. It proves the automatic collection/export/audit path now works without the earlier obvious text leakage.

To become thesis-grade, the next dataset must scale this same balanced design to at least 2,000 real collected samples, include 300-500 manually reviewed samples, and add real-agent `ACTION_MISMATCH` / `LOOP_DETECTED` cases from observed agent executions rather than synthetic injection metadata.

## Why This Is Needed

The current synthetic 70k dataset is mechanically trainable, but outcome and failure labels are deterministic from synthetic metadata. A model can solve those labels without using screenshots. The gold dataset must therefore use observed browser behavior and must export training files without leaked fields.

## Shared Label Policy

The model heads stay compatible with the synthetic dataset:

- `outcome_label`: `SUCCESS`, `FAILURE`
- `failure_type_4`: `NONE`, `ACTION_MISMATCH`, `PERCEPTION_ERROR`, `LOOP_DETECTED`
- `recovery_strategy`: `NONE`, `RETRY`, `REPLAN`, `BACKTRACK`, `ALTERNATIVE_TARGET`
- `action_type`: `CLICK`, `TYPE`, `SELECT`

The gold audit file also stores `failure_type_fine` for real observed failures such as `tool_failure`, `state_no_change`, `ui_variation`, and `unknown`.

If a fine label does not safely map into the 4-class synthetic label set, the exporter sets:

```json
{
  "failure_type_4": null,
  "failure_type_4_eval_mask": false
}
```

Those samples still train outcome/action/recovery heads, but they are skipped for 4-class failure-type loss and metrics.

Similarly, real gold collection may include `WAIT`, `NAVIGATE`, `SCROLL`, `HOVER`, or `PRESS_KEY`. These are kept in the audit file, but the export sets `action_type_eval_mask=false` for actions outside the synthetic action head (`CLICK`, `TYPE`, `SELECT`).

## Forbidden Model Input Fields

These fields may appear in `gold_audit.jsonl`, but must not appear in model-training exports:

- `injection_type`
- `is_augmented`
- `agent_confidence_before`
- `failure_confidence`
- `visual_diff_score`
- `memory_update_flag`
- `recovery_success`
- `pixel_diff`
- `ssim`
- `page_status`
- `http_status`
- `error_message`
- `url_before`
- `url_after`
- `failure_type_fine`
- review/status metadata

## Implemented Components

- `src/gold_collection/gold_schema.py`
  - Shared labels, fine-to-coarse mapping, forbidden-field list, `GoldStep`, and `GoldTrajectory`.
- `src/gold_collection/gold_collector.py`
  - Reuses `BrowserReplay`, `MetricComputer`, and the existing failure decision tree to collect observed browser steps.
  - Writes full audit rows to `output/gold_dataset/gold_audit.jsonl`.
- `src/gold_collection/gold_exporter.py`
  - Splits by `task_id` and writes leakage-safe train/val/test files.
- `src/gold_collection/gold_review.py`
  - Builds JSONL and HTML review queues.
- `scripts/collect_gold_pilot.py`
  - Small pilot run.
- `scripts/collect_gold_dataset.py`
  - Main collection from an ActionLog JSON/JSONL file.
- `scripts/export_gold_for_training.py`
  - Creates model-safe split files.
- `scripts/validate_gold_dataset.py`
  - Validates audit and exported splits.
- `scripts/audit_gold_task_seed.py`
  - Checks ActionLog seed files before collection for one-sided task/action text shortcuts.
- `scripts/audit_gold_leakage.py`
  - Checks exported model splits for explicit keyword leakage, pure failure tokens, and text-only shortcut baselines.
- `scripts/build_gold_review.py`
  - Creates review artifacts.

## Collection Workflow

1. Prepare an ActionLog JSONL file with stable controlled/custom tasks.
2. Run a 20-100 sample pilot:

```bash
python scripts/collect_gold_pilot.py --log-file logs/gold_tasks.jsonl --limit 50
```

3. Validate the pilot:

```bash
python scripts/validate_gold_dataset.py --base-dir output/gold_dataset
```

4. Build review artifacts:

```bash
python scripts/build_gold_review.py --limit 500
```

5. After pilot quality is acceptable, collect the main dataset:

```bash
python scripts/collect_gold_dataset.py --log-file logs/gold_tasks.jsonl --limit 2000
```

6. Export leakage-safe train/val/test files:

```bash
python scripts/export_gold_for_training.py
```

7. Validate exported splits:

```bash
python scripts/validate_gold_dataset.py
```

## Acceptance Criteria

- No missing screenshots in audit rows.
- No duplicate `sample_id`.
- No task overlap between train/val/test exports.
- Exported split files contain no forbidden fields.
- Every repeated model-visible task/action phrase has both success and failure examples before collection.
- Text-only leakage baselines must stay near chance and must not reach strong MCC on validation/test splits.
- Unknown or unmapped fine labels remain below 10% after manual review.
- Actions outside `CLICK`/`TYPE`/`SELECT` are masked for action-head loss/metrics.
- Metadata-only baseline should not solve the gold test set perfectly.
- Final thesis results must report gold-test performance separately from synthetic-pretraining performance.

## Next Milestones

1. Manually review the 32-row v3 pilot in `output/gold_dataset_final_v3_balanced/review/review.html`.
2. Expand the v3 task template to 300-500 balanced tasks across more domains and intents.
3. Run `scripts/audit_gold_task_seed.py` before every collection batch.
4. Collect a 300-500 sample pilot, then export, validate, and run `scripts/audit_gold_leakage.py`.
5. Add real agent-run data for `ACTION_MISMATCH` and `LOOP_DETECTED`.
6. Scale to 2,000+ samples only after the pilot passes structure, image, manual-review, and leakage checks.
