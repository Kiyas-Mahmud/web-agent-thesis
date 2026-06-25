# Gold Dataset V8 Reproduction Handoff

This note records how the current thesis gold dataset was made, what files/folders were touched, and how another agent should continue or recreate the work.

Read these first:

- `docs/FINAL_GOLD_COLLECTION_RUNBOOK.md`
- `docs/GOLD_DATASET_COLLECTION_IMPLEMENTATION.md`

Do not treat the old synthetic 70k dataset as final Q1/A* evidence. It is only for pipeline checks or optional pretraining. The final thesis dataset must be real-browser collected, leakage-audited, manually reviewed, multimodal, and gate-passing.

## Current Approved Baseline

Approved dataset folder:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

This is the current approved 2,032-sample real-browser gold baseline.

Approved-only gate result:

```text
rows: 2032
train: 1219
val: 406
test: 407
task overlap: 0
success: 974
failure: 1058
NONE: 974
PERCEPTION_ERROR: 456
ACTION_MISMATCH: 451
LOOP_DETECTED: 151
recovery NONE: 974
recovery ALTERNATIVE_TARGET: 456
recovery BACKTRACK: 451
recovery REPLAN: 151
```

All rows in this folder have:

```text
review_status=approved
```

The approved review page is:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\review\review.html
```

Backup before approval:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.before_approval_20260623_005637.jsonl
```

Backup before the recovery-label fix:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.before_recoveryfix.jsonl
```

## Why V8 Exists

Earlier v6 data reduced the simple visual-diff shortcut by adding failures where the page can change but the action is wrong. However, those labels were still based on designed seed actions, not a separate online browser agent making its own mistakes.

V7 introduced an online goal-only browser-agent collector. The seed gives the page and goal; the agent chooses from live browser candidates. This creates more realistic `ACTION_MISMATCH` and `LOOP_DETECTED` failures.

V8 scaled that idea to a 2k approved baseline.

## Repo Files Touched Or Created

These files exist in the repo working tree and are part of the gold-data work. At the time of this handoff many are untracked, so another agent must not assume they are committed.

Seed/config files:

```text
config/gold_tasks_final_v3_balanced.jsonl
config/gold_tasks_final_v4_300.jsonl
config/gold_tasks_final_v5_visual_300.jsonl
config/gold_tasks_final_v6_action_mismatch_300.jsonl
config/gold_tasks_final_v6_full_observed_320.jsonl
config/gold_tasks_final_v7_agent_smoke_60.jsonl
config/gold_tasks_final_v7_agent_330.jsonl
config/gold_tasks_final_v7_agent_320_retry1.jsonl
config/gold_tasks_final_v8_agent_2107.jsonl
config/gold_tasks_final_v8_agent_2107_retry_missing.jsonl
config/gold_tasks_final_v8_agent_2107_retry2_remaining.jsonl
```

Collector/postprocess scripts added during the work:

```text
scripts/collect_gold_agent_v7.py
scripts/postprocess_gold_v6_observed_labels.py
```

Existing gate scripts used:

```text
scripts/audit_gold_task_seed.py
scripts/collect_gold_dataset.py
scripts/export_gold_for_training.py
scripts/validate_gold_dataset.py
scripts/audit_gold_leakage.py
scripts/check_gold_images.py
scripts/build_gold_review.py
```

This handoff file:

```text
docs/GOLD_DATASET_V8_REPRODUCTION_HANDOFF.md
```

## External Data Folders Created

Large generated data was kept outside the repo on:

```text
G:\thesis_gold
```

Important folders:

```text
G:\thesis_gold\gold_dataset_final_v3_balanced_retry
G:\thesis_gold\gold_dataset_final_v3_balanced_retry2
G:\thesis_gold\gold_dataset_final_v4_300
G:\thesis_gold\gold_dataset_final_v4_300_smoke
G:\thesis_gold\gold_dataset_final_v5_visual_300
G:\thesis_gold\gold_dataset_final_v5_visual_300_smoke
G:\thesis_gold\gold_dataset_final_v5_visual_300_smoke2
G:\thesis_gold\gold_dataset_final_v6_action_mismatch_300_smoke
G:\thesis_gold\gold_dataset_final_v6_action_mismatch_300_smoke2
G:\thesis_gold\gold_dataset_final_v6_full_observed_320
G:\thesis_gold\gold_dataset_final_v7_agent_smoke_60
G:\thesis_gold\gold_dataset_final_v7_agent_330
G:\thesis_gold\gold_dataset_final_v7_agent_320_retry1
G:\thesis_gold\gold_dataset_final_v7_agent_320_retry2
G:\thesis_gold\gold_dataset_final_v7_agent_320_policycheck
G:\thesis_gold\gold_dataset_final_v8_agent_2107
G:\thesis_gold\gold_dataset_final_v8_agent_2107_retry_missing
G:\thesis_gold\gold_dataset_final_v8_agent_2107_retry2_remaining
G:\thesis_gold\gold_dataset_final_v8_agent_2107_combined
G:\thesis_gold\gold_dataset_final_v8_agent_2107_clean
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

Do not store large collected image/replay folders inside the repo.

## Important Dataset Stages

### V3 Pilot

Seed:

```text
config/gold_tasks_final_v3_balanced.jsonl
```

Purpose:

- Reproduce the clean 32-task pilot.
- Validate the pipeline.
- Not final thesis evidence by itself.

### V6 Scale-From Batch

Seed:

```text
config/gold_tasks_final_v6_full_observed_320.jsonl
```

Output:

```text
G:\thesis_gold\gold_dataset_final_v6_full_observed_320
```

Status:

```text
rows: 320
review_status=approved
success: 164
failure: 156
ACTION_MISMATCH: 80
PERCEPTION_ERROR: 41
LOOP_DETECTED: 35
```

Purpose:

- Clean scale-from batch.
- Still not enough for final thesis scale.
- Helped reveal that simple no-change failures were too easy.

### V7 Agent Batch

Main output:

```text
G:\thesis_gold\gold_dataset_final_v7_agent_320_retry2
```

Status after filtering a leakage-prone `about page` pattern:

```text
rows: 301
review_status=approved
success: 145
failure: 156
ACTION_MISMATCH: 71
PERCEPTION_ERROR: 63
LOOP_DETECTED: 22
```

Important V7 design:

- The collector is `scripts/collect_gold_agent_v7.py`.
- The seed gives goals/oracles, not exact fixed replay actions.
- The browser agent chooses live page elements.
- `action_target_desc` is sanitized to neutral text:

```text
Agent clicked page element
```

- Raw clicked text is kept only in metadata:

```text
metadata.raw_action_target_desc
metadata.agent_action
```

Training exports exclude metadata, so raw target text does not leak labels.

### V8 2k Batch

Main seed:

```text
config/gold_tasks_final_v8_agent_2107.jsonl
```

First pass output:

```text
G:\thesis_gold\gold_dataset_final_v8_agent_2107
```

The first pass stopped late because of collection/network instability. It produced 1,687 rows.

Retry seed/output:

```text
config/gold_tasks_final_v8_agent_2107_retry_missing.jsonl
G:\thesis_gold\gold_dataset_final_v8_agent_2107_retry_missing
```

Second retry seed/output:

```text
config/gold_tasks_final_v8_agent_2107_retry2_remaining.jsonl
G:\thesis_gold\gold_dataset_final_v8_agent_2107_retry2_remaining
```

Merged output:

```text
G:\thesis_gold\gold_dataset_final_v8_agent_2107_combined
```

Merged count:

```text
rows: 2088
unique sample ids: 2088
```

This merged folder had 56 blank-like screenshots, so it was not accepted directly.

Cleaned output after removing blank-like screenshot rows:

```text
G:\thesis_gold\gold_dataset_final_v8_agent_2107_clean
```

Cleaned count:

```text
rows: 2032
```

Then a recovery-label issue was found in manual review.

Corrected and approved output:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

## Recovery BACKTRACK Fix

Manual review found a bad auto-label pattern:

```text
url_before: https://example.org/page/
url_after:  https://example.org/page/#
pixel_diff: 0.0
ssim: 1.0
old label: ACTION_MISMATCH + BACKTRACK
```

This is not a true wrong-page navigation. The page did not visually change. The agent clicked a useless fragment/hash target or missed the real target.

Correction applied:

```text
failure_type_4: PERCEPTION_ERROR
failure_type_fine: perception_error
recovery_strategy_observed: ALTERNATIVE_TARGET
```

Rows fixed:

```text
29
```

Remaining bad pattern after fix:

```text
0
```

The original labels were preserved inside metadata:

```text
metadata.recoveryfix_original_label
metadata.recoveryfix_rule
```

Do not reintroduce `BACKTRACK` for fragment-only no-visual-change cases.

## Correct Meaning Of Recovery Labels

Use this interpretation during review:

```text
NONE
  Success row. No recovery needed.

ALTERNATIVE_TARGET
  The agent should click/type/select a different visible target on the same page.
  Use for no-op clicks, wrong inert clicks, wrong field, or missed target where the page did not truly navigate away.

BACKTRACK
  The agent opened the wrong page or moved to a wrong state and should go back.
  Example: task says open API page, but agent opens Installation page.

REPLAN
  The agent repeats/searches/clicks without progress and needs a new plan.
  This is appropriate for LOOP_DETECTED, especially after multiple no-progress steps.

RETRY
  Same action should be tried again because of a transient issue.

ABORT
  Page/task is blocked or unrecoverable.
```

## Standard Gate Sequence

Use the project venv Python:

```powershell
.\.venv\Scripts\python.exe
```

Audit a seed before collecting:

```powershell
.\.venv\Scripts\python.exe scripts\audit_gold_task_seed.py `
  --log-file config\gold_tasks_final_v8_agent_2107.jsonl `
  --fail-on-blockers
```

Collect with the agent collector:

```powershell
.\.venv\Scripts\python.exe scripts\collect_gold_agent_v7.py `
  --task-file config\gold_tasks_final_v8_agent_2107.jsonl `
  --output-dir G:\thesis_gold\gold_dataset_final_v8_agent_2107 `
  --limit 2107 `
  --timeout-ms 30000 `
  --headless
```

Export:

```powershell
.\.venv\Scripts\python.exe scripts\export_gold_for_training.py `
  --audit-file G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.jsonl `
  --output-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

For the final approved export, always use `--approved-only`:

```powershell
.\.venv\Scripts\python.exe scripts\export_gold_for_training.py `
  --audit-file G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.jsonl `
  --output-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser `
  --approved-only
```

Validate:

```powershell
.\.venv\Scripts\python.exe scripts\validate_gold_dataset.py `
  --base-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser `
  --audit-file G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.jsonl
```

Leakage audit:

```powershell
.\.venv\Scripts\python.exe scripts\audit_gold_leakage.py `
  --base-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

Image check:

```powershell
.\.venv\Scripts\python.exe scripts\check_gold_images.py `
  --base-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

Build review:

```powershell
.\.venv\Scripts\python.exe scripts\build_gold_review.py `
  --audit-file G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\gold_audit.jsonl `
  --output-dir G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\review `
  --limit 2500
```

## Manual Review Rules

Open the review HTML and check the before/after screenshots:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser\review\review.html
```

Review each row for:

- Is the task visible and understandable?
- Did the agent action match the task?
- If outcome is `SUCCESS`, did the final page/state satisfy the goal?
- If outcome is `FAILURE`, is the coarse failure type correct?
- Is recovery correct?
- Is there a text shortcut in task/action/domain that reveals the label?
- Is the image blank, broken, tiny, or visually unusable?
- Is the failure just a visual no-change shortcut?

Approval means the human reviewer accepts the label. It does not mean the batch is a larger 30k final dataset.

## How To Approve A Reviewed Batch

Only approve after manual review.

Before editing approval status, make a backup:

```text
gold_audit.before_approval_YYYYMMDD_HHMMSS.jsonl
```

Then set:

```text
review_status=approved
```

for rows that passed review. Do not approve rows that were not checked.

After approval, rerun the approved-only gate sequence:

```text
export --approved-only
validate
leakage audit
image check
review rebuild
```

## If Recreating V8 From Scratch

Recommended process:

1. Confirm `.venv` is installed from the runbook.
2. Confirm `scripts/collect_gold_agent_v7.py` exists.
3. Audit the seed first.
4. Collect to a new folder under `G:\thesis_gold`, not inside the repo.
5. If collection stops early, identify missing task IDs and create a retry seed.
6. Merge original and retry rows by unique `sample_id` or `task_id`.
7. Check for duplicates.
8. Remove rows with bad or blank-like screenshots.
9. Export.
10. Validate.
11. Run leakage audit.
12. Run image check.
13. Build review.
14. Manually review.
15. Correct labels if needed.
16. Back up the audit file.
17. Mark approved rows.
18. Export with `--approved-only`.
19. Rerun all gates.

Do not call the recreated dataset final unless every step above passes.

## If Scaling Beyond 2k

Do not jump straight to a claimed 30k gold dataset.

Recommended scale path:

```text
2k approved gold baseline
5k real-browser batch
10k real-browser batch
30k real-browser batch
```

For each scale batch:

- Create/audit seed first.
- Collect in a separate output folder.
- Keep retry folders separate.
- Merge only after checking duplicate IDs.
- Run gates before review.
- Review a meaningful sample or the full batch depending on thesis claim.
- Only approved rows can be called gold.

Careful thesis wording:

```text
30k unreviewed/auto-labeled = real-browser silver or weak-labeled expansion.
30k manually reviewed + gates passed = gold.
2k approved + 30k unreviewed = 2k gold plus 30k real-browser expansion.
```

## Known Risks To Watch

### Visual-Diff Shortcut

V8 still has a visual-diff diagnostic where image-change alone can predict many outcomes:

```text
same_data_best_accuracy: 0.7889
```

This does not fail the current gate, but it is a warning for modeling. Future batches should include more failures where the page changes but the action is wrong, and more successes/failures that cannot be solved by "image changed = success".

### Text Leakage

Keep `action_target_desc` neutral for agent-collected rows:

```text
Agent clicked page element
```

Do not put the clicked label, URL, domain-specific clue, or expected answer in training-visible fields.

Raw clicked text belongs only in metadata, which the exporter removes.

### Domain Or Task Shortcuts

Avoid tasks where one task phrase appears only in failures or only in successes.

The earlier `Open the about page.` pattern was removed from v7 because it became failure-only leakage.

### Recovery Label Confusion

Do not label no-op hash/fragment changes as `BACKTRACK`.

Use:

```text
PERCEPTION_ERROR + ALTERNATIVE_TARGET
```

for same-page, no-visual-change useless clicks.

Use:

```text
ACTION_MISMATCH + BACKTRACK
```

when the agent actually opens the wrong page.

Use:

```text
LOOP_DETECTED + REPLAN
```

when the agent repeats without progress.

## Current Start Point For Another Agent

Start from:

```text
G:\thesis_gold\web_agent_gold_v8_approved_2032_real_browser
```

Treat it as:

```text
approved 2,032-sample real-browser gold baseline
```

Then either:

1. Run experiments from its exported splits, or
2. Create the next larger seed and collect a new scale batch under a new `G:\thesis_gold\...` folder.

Do not overwrite the approved v8 folder. Create a new folder for each new run.

