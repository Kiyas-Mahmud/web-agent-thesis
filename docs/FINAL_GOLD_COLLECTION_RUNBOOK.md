# Final Gold Dataset Collection Runbook

This file is the handoff guide for continuing the thesis gold-data collection on another desktop.

## Goal

Build a real-browser, leakage-audited multimodal gold dataset for the thesis model.

The final thesis claim must be based on real collected browser behavior, not only the old synthetic 70k dataset. The synthetic 70k dataset can still be used for pipeline testing or optional pretraining, but not as the final evidence for a Q1/A* multimodal failure-diagnosis claim.

Target final dataset:

- At least 2,000 real collected gold samples.
- 300-500 manually reviewed samples.
- Balanced success/failure examples.
- Multiple real failure types: `PERCEPTION_ERROR`, `ACTION_MISMATCH`, `LOOP_DETECTED`.
- No metadata, task text, domain, or simple visual-diff shortcut should solve the labels.
- Final paper results must report real gold-test performance separately from synthetic-pretraining performance.

## What We Did On This PC

The old synthetic dataset was audited and found unsuitable as the final thesis gold dataset because labels were recoverable from synthetic metadata/rules.

We then built a real-browser collection path:

- `src/gold_collection/gold_collector.py` collects real browser screenshots and audit labels.
- `src/gold_collection/gold_exporter.py` exports leakage-safe train/val/test JSON files.
- `scripts/audit_gold_task_seed.py` checks a task seed before collection.
- `scripts/audit_gold_leakage.py` checks exported splits for text leakage and shortcut baselines.
- `scripts/check_gold_images.py` checks screenshot integrity and visual-diff shortcut strength.
- `config/gold_tasks_final_v3_balanced.jsonl` is the tracked 32-task clean seed.

The local pilot collection was written to `output/gold_dataset_final_v3_balanced`, but `output/` is intentionally ignored by git and will not be pushed.

Pilot result:

- 32 tasks collected automatically with Playwright.
- 64 screenshots.
- 16 `SUCCESS`, 16 `FAILURE`.
- 16 `NONE`, 16 `PERCEPTION_ERROR`.
- 0 missing images.
- 0 split task overlap.
- 0 forbidden fields in exported splits.
- Seed audit passed.
- Dataset validation passed.
- Text leakage audit passed.
- Image files were valid, 1280x720, and nonblank.

Important limitation:

- This is a valid pilot/protocol dataset, not the final thesis dataset.
- It only covers `PERCEPTION_ERROR`.
- It is still visually simple: most failures have almost no before/after change, while successes usually change the page. A visual-diff threshold was strong on the 32-row pilot.

## Repository Structure

Important folders:

- `config/`: tracked task seeds and config files.
- `scripts/`: collection, export, validation, audit, review, and image-check commands.
- `src/browser_replay/`: Playwright replay engine.
- `src/browser_recorder/`: browser action execution and screenshot capture.
- `src/gold_collection/`: gold schema, collector, exporter, and review builder.
- `docs/`: project notes and this runbook.
- `output/`: generated datasets, ignored by git.
- `logs/`: local logs and scratch task files, ignored by git.

Important files:

- `config/gold_tasks_final_v3_balanced.jsonl`
- `scripts/collect_gold_dataset.py`
- `scripts/export_gold_for_training.py`
- `scripts/validate_gold_dataset.py`
- `scripts/audit_gold_task_seed.py`
- `scripts/audit_gold_leakage.py`
- `scripts/check_gold_images.py`
- `scripts/build_gold_review.py`
- `docs/GOLD_DATASET_COLLECTION_IMPLEMENTATION.md`

## Environment Setup On New Desktop

Use a desktop with enough disk space. Keep generated data on a large drive, for example `D:\thesis_gold`.

Clone the branch:

```powershell
git clone -b Dataset https://github.com/Kiyas-Mahmud/web-agent-thesis.git
cd web-agent-thesis
```

Create and activate a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell blocks activation, use the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Quick import check:

```powershell
python scripts/verify_imports.py
python -m py_compile scripts/audit_gold_task_seed.py scripts/audit_gold_leakage.py scripts/check_gold_images.py
```

## Reproduce The Clean 32-Task Pilot

First check the seed before collecting:

```powershell
python scripts/audit_gold_task_seed.py --log-file config/gold_tasks_final_v3_balanced.jsonl --fail-on-blockers
```

Collect the pilot on a large drive:

```powershell
python scripts/collect_gold_dataset.py `
  --log-file config/gold_tasks_final_v3_balanced.jsonl `
  --output-dir D:\thesis_gold\gold_dataset_final_v3_balanced `
  --limit 32 `
  --timeout-ms 30000 `
  --step-delay-ms 300
```

Export leakage-safe train/val/test files:

```powershell
python scripts/export_gold_for_training.py `
  --audit-file D:\thesis_gold\gold_dataset_final_v3_balanced\gold_audit.jsonl `
  --output-dir D:\thesis_gold\gold_dataset_final_v3_balanced
```

Validate structure and splits:

```powershell
python scripts/validate_gold_dataset.py `
  --base-dir D:\thesis_gold\gold_dataset_final_v3_balanced `
  --audit-file D:\thesis_gold\gold_dataset_final_v3_balanced\gold_audit.jsonl
```

Audit exported text leakage:

```powershell
python scripts/audit_gold_leakage.py --base-dir D:\thesis_gold\gold_dataset_final_v3_balanced
```

Check screenshots and visual-diff shortcuts:

```powershell
python scripts/check_gold_images.py --base-dir D:\thesis_gold\gold_dataset_final_v3_balanced
```

Build manual review files:

```powershell
python scripts/build_gold_review.py `
  --audit-file D:\thesis_gold\gold_dataset_final_v3_balanced\gold_audit.jsonl `
  --output-dir D:\thesis_gold\gold_dataset_final_v3_balanced\review `
  --limit 200
```

Open:

```text
D:\thesis_gold\gold_dataset_final_v3_balanced\review\review.html
```

## How To Scale Correctly

Do not immediately run a huge 2,000-sample collection from a new seed. Scale in stages.

Stage 1:

- Create `config/gold_tasks_final_v4_300.jsonl`.
- Aim for 300-500 tasks.
- Keep task text balanced: every repeated task phrase must have both success and failure examples.
- Keep action type balanced: no action type should appear only in success or only in failure.
- Keep domain balance reasonable: do not let one domain mean success and another domain mean failure.
- Run `scripts/audit_gold_task_seed.py` before collection.

Stage 2:

- Collect 300-500 real samples.
- Export, validate, run leakage audit, run image audit, build review HTML.
- Manually review at least 100 samples from this pilot.
- Fix seed/task design if any shortcut appears.

Stage 3:

- Add real agent-run failures for `ACTION_MISMATCH` and `LOOP_DETECTED`.
- These should come from observed agent behavior, not synthetic hidden metadata.
- Keep labels manually reviewable.

Stage 4:

- Only after the 300-500 pilot passes, scale to 2,000+.
- Manually review 300-500 samples.
- Freeze final train/val/test splits.

## Required Validity Gates

A batch can continue only if all of these are true:

- `audit_gold_task_seed.py` reports no blockers.
- `validate_gold_dataset.py` passes.
- `audit_gold_leakage.py` reports no obvious text leakage.
- `check_gold_images.py` reports no bad/blank/small images.
- No split task overlap.
- No forbidden fields in exported splits.
- Outcome labels are not solved by metadata, ids, task text, action text, or domain.
- Visual-diff-only baseline is reported and discussed. If it is very strong, the next seed must include harder cases.
- Manual review finds labels visually/behaviorally defensible.

## What To Ask The Agent On The New Desktop

Use this as the first prompt to the agent:

```text
Read docs/FINAL_GOLD_COLLECTION_RUNBOOK.md and docs/GOLD_DATASET_COLLECTION_IMPLEMENTATION.md.
We need to continue final thesis gold-data collection.
First reproduce the 32-task v3 pilot using config/gold_tasks_final_v3_balanced.jsonl on a large output drive.
Then run seed audit, collection, export, validation, leakage audit, image audit, and build review HTML.
Do not claim the data is final until the gates pass.
After the pilot passes, help design config/gold_tasks_final_v4_300.jsonl with balanced success/failure, more domains, and real ACTION_MISMATCH/LOOP_DETECTED collection plan.
```

## Notes For Publication Claims

Safe claim now:

```text
We implemented and validated a leakage-aware real-browser gold collection protocol.
The v3 pilot passes structural and text-leakage checks and is suitable for pipeline verification.
```

Unsafe claim now:

```text
We have the final gold dataset for Q1/A* multimodal failure diagnosis.
```

That final claim requires the scaled, manually reviewed, multi-failure-type dataset.
