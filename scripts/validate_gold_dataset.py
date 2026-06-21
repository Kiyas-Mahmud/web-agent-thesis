"""Validate gold audit and exported model files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gold_collection.gold_schema import FORBIDDEN_TRAINING_FIELDS, GoldStep  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_audit(audit_file: Path, base_dir: Path) -> list[str]:
    blockers: list[str] = []
    rows = load_jsonl(audit_file)
    steps = [GoldStep(**row) for row in rows]
    ids = [step.sample_id for step in steps]
    missing_images = [
        step.sample_id for step in steps
        if step.state_before and step.state_after and not step.paths_exist(base_dir)
    ]

    print("Audit")
    print(f"  rows: {len(steps)}")
    print(f"  sample_id unique: {len(set(ids))}/{len(ids)}")
    print(f"  missing images: {len(missing_images)}")
    print(f"  outcome: {dict(Counter(step.outcome_label for step in steps).most_common())}")
    print(f"  failure fine: {dict(Counter(step.failure_type_fine for step in steps).most_common())}")
    print(f"  failure coarse: {dict(Counter(step.failure_type_4 for step in steps).most_common())}")
    print(f"  coarse mask false: {sum(1 for step in steps if not step.failure_type_4_eval_mask)}")

    if len(ids) != len(set(ids)):
        blockers.append("duplicate sample_id values in audit")
    if missing_images:
        blockers.append("audit has missing image paths")
    return blockers


def validate_splits(base_dir: Path) -> list[str]:
    blockers: list[str] = []
    split_rows = {}
    for split_name in ("train", "val", "test"):
        path = base_dir / f"split_{split_name}.json"
        if not path.is_file():
            continue
        split_rows[split_name] = json.loads(path.read_text(encoding="utf-8"))

    if not split_rows:
        print("Splits: none exported yet")
        return blockers

    print("Splits")
    task_sets = {}
    for split_name, rows in split_rows.items():
        task_sets[split_name] = {row["task_id"] for row in rows}
        leaked = sorted({field for row in rows for field in row if field in FORBIDDEN_TRAINING_FIELDS})
        print(f"  {split_name}: rows={len(rows)}, tasks={len(task_sets[split_name])}, leaked={leaked}")
        if leaked:
            blockers.append(f"split_{split_name}.json contains forbidden fields: {leaked}")

    if {"train", "val", "test"} <= set(task_sets):
        overlaps = {
            "train_val": len(task_sets["train"] & task_sets["val"]),
            "train_test": len(task_sets["train"] & task_sets["test"]),
            "val_test": len(task_sets["val"] & task_sets["test"]),
        }
        print(f"  task overlaps: {overlaps}")
        if any(overlaps.values()):
            blockers.append("task leakage between exported splits")
    return blockers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate gold dataset files.")
    parser.add_argument("--base-dir", type=Path, default=Path("output/gold_dataset"))
    parser.add_argument("--audit-file", type=Path, default=Path("output/gold_dataset/gold_audit.jsonl"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blockers: list[str] = []

    if args.audit_file.is_file():
        blockers.extend(validate_audit(args.audit_file, args.base_dir))
    else:
        blockers.append(f"missing audit file: {args.audit_file}")

    blockers.extend(validate_splits(args.base_dir))

    print("Verdict")
    if blockers:
        for blocker in blockers:
            print(f"  BLOCKER: {blocker}")
        return 1
    print("  GOLD DATASET VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
