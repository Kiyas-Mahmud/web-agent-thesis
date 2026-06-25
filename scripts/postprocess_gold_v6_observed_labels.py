"""Post-process v6 gold audit rows using observed browser behavior.

The generic collector treats a mechanically successful wrong click as success.
For v6, wrong-action rows are candidate failures only when the browser actually
changed state after the wrong target was executed. Loop rows are candidate
failures only after repeated no-progress steps are observed in the trajectory.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


NO_CHANGE_PIXEL_DIFF = 0.01
HIGH_SSIM = 0.99


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_seed_metadata(path: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        metadata[str(row["task_id"])] = row.get("metadata") or {}
    return metadata


def raw_label(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "outcome_label": row.get("outcome_label"),
        "failure_type_4": row.get("failure_type_4"),
        "failure_type_fine": row.get("failure_type_fine"),
    }


def changed_state(row: dict[str, Any]) -> bool:
    before = str(row.get("url_before") or "")
    after = str(row.get("url_after") or "")
    pixel_diff = row.get("pixel_diff")
    try:
        visual_changed = pixel_diff is not None and float(pixel_diff) >= NO_CHANGE_PIXEL_DIFF
    except (TypeError, ValueError):
        visual_changed = False
    return (before and after and before != after) or visual_changed


def no_progress(row: dict[str, Any]) -> bool:
    before = str(row.get("url_before") or "")
    after = str(row.get("url_after") or "")
    same_url = bool(before and after and before == after)
    pixel_diff = row.get("pixel_diff")
    ssim = row.get("ssim")
    try:
        low_diff = pixel_diff is not None and float(pixel_diff) < NO_CHANGE_PIXEL_DIFF
    except (TypeError, ValueError):
        low_diff = False
    try:
        high_ssim = ssim is not None and float(ssim) > HIGH_SSIM
    except (TypeError, ValueError):
        high_ssim = False
    return same_url and (low_diff or high_ssim)


def set_failure(row: dict[str, Any], *, fine: str, coarse: str, recovery: str, reason: str) -> None:
    metadata = row.setdefault("metadata", {})
    metadata.setdefault("raw_auto_label", raw_label(row))
    metadata["observed_relabel_reason"] = reason
    row["outcome_label"] = "FAILURE"
    row["failure_type_fine"] = fine
    row["failure_type_4"] = coarse
    row["failure_type_4_eval_mask"] = True
    row["recovery_strategy_observed"] = recovery
    row["label_source"] = "auto_observed_v6"
    row["review_status"] = "pending"


def process(rows: list[dict[str, Any]], seed_meta: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    summary: Counter[str] = Counter()
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_id"))].append(row)

    for task_id, task_rows in by_task.items():
        task_rows.sort(key=lambda row: int(row.get("step_index") or 0))
        meta = seed_meta.get(task_id, {})
        target = str(meta.get("failure_type_target") or "").upper()

        if target == "ACTION_MISMATCH":
            for row in task_rows:
                if row.get("failure_type_fine") == "none" and changed_state(row):
                    metadata = row.setdefault("metadata", {})
                    metadata["v6_failure_type_target"] = "ACTION_MISMATCH"
                    metadata["intended_target_desc"] = meta.get("intended_target_desc")
                    metadata["wrong_target_desc"] = meta.get("wrong_target_desc")
                    set_failure(
                        row,
                        fine="action_mismatch",
                        coarse="ACTION_MISMATCH",
                        recovery="BACKTRACK",
                        reason=(
                            "Observed wrong-target action changed browser state "
                            "(URL changed or visual diff exceeded threshold)."
                        ),
                    )
                    summary["action_mismatch"] += 1
                else:
                    summary["action_mismatch_not_observed"] += 1

        if target == "LOOP_DETECTED":
            no_progress_seen = 0
            for row in task_rows:
                if no_progress(row):
                    no_progress_seen += 1
                else:
                    no_progress_seen = 0
                metadata = row.setdefault("metadata", {})
                metadata["v6_failure_type_target"] = "LOOP_DETECTED"
                if row.get("failure_type_fine") == "none" and no_progress_seen >= 3:
                    set_failure(
                        row,
                        fine="loop_detected",
                        coarse="LOOP_DETECTED",
                        recovery="BACKTRACK",
                        reason=(
                            "Observed repeated no-progress browser actions in the same task "
                            "after at least three consecutive unchanged states."
                        ),
                    )
                    summary["loop_detected"] += 1
                else:
                    summary["loop_not_observed"] += 1

    summary.update(Counter(str(row.get("failure_type_4")) for row in rows))
    return rows, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relabel v6 gold rows from observed behavior.")
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_jsonl(args.audit_file)
    seed_meta = load_seed_metadata(args.seed_file)
    rows, summary = process(rows, seed_meta)
    output = args.output_file or args.audit_file
    write_jsonl(output, rows)
    print(json.dumps({"rows": len(rows), "summary": dict(summary)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
