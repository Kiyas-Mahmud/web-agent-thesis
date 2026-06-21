"""Final dataset trainability checker.

This script validates the canonical split files used for thesis model training:

    output/dataset_70k_safe/split_train.json
    output/dataset_70k_safe/split_val.json
    output/dataset_70k_safe/split_test.json

It checks schema completeness, label maps, split leakage, image references,
numeric ranges, bbox masking, and a small PIL/NumPy batch smoke test.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np
from PIL import Image


BASE_DIR = Path("output/dataset_70k_safe")
SPLIT_FILES = {
    "train": "split_train.json",
    "val": "split_val.json",
    "test": "split_test.json",
}

REQUIRED_FIELDS = [
    "task_id",
    "task_description",
    "website_domain",
    "state_before",
    "state_after",
    "visual_diff_score",
    "action_type",
    "action_target_desc",
    "action_coordinates",
    "execution_outcome",
    "failure_type",
    "failure_confidence",
    "recovery_strategy",
    "recovery_success",
    "agent_confidence_before",
    "reflection_text",
    "memory_update_flag",
    "original_task_id",
    "split",
    "pass",
    "is_augmented",
    "injection_type",
    "action_target_bbox",
    "borrowed_image",
]

LABEL_MAPS = {
    "execution_outcome": {"SUCCESS": 0, "FAILURE": 1},
    "failure_type": {
        "NONE": 0,
        "ACTION_MISMATCH": 1,
        "PERCEPTION_ERROR": 2,
        "LOOP_DETECTED": 3,
    },
    "action_type": {"CLICK": 0, "TYPE": 1, "SELECT": 2},
    "recovery_strategy": {
        "NONE": 0,
        "RETRY": 1,
        "REPLAN": 2,
        "BACKTRACK": 3,
        "ALTERNATIVE_TARGET": 4,
        "ABORT": 5,
    },
}

NUMERIC_0_1_FIELDS = [
    "visual_diff_score",
    "failure_confidence",
    "agent_confidence_before",
]


def load_splits(base_dir: Path) -> dict[str, list[dict[str, Any]]]:
    splits: dict[str, list[dict[str, Any]]] = {}
    for split_name, file_name in SPLIT_FILES.items():
        path = base_dir / file_name
        if not path.is_file():
            raise FileNotFoundError(f"Missing split file: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise TypeError(f"{path} must contain a JSON list")
        splits[split_name] = data
    return splits


def pct(num: int, den: int) -> str:
    return f"{(num / max(1, den)) * 100:.2f}%"


def validate_schema(rows: list[dict[str, Any]], blockers: list[str]) -> None:
    missing = Counter()
    nulls = Counter()
    empty = Counter()

    for row in rows:
        for field in REQUIRED_FIELDS:
            if field not in row:
                missing[field] += 1
            elif row[field] is None:
                nulls[field] += 1
            elif row[field] == "":
                empty[field] += 1

    print("\nSchema")
    print(f"  missing fields: {dict(missing) or 'none'}")
    print(f"  null fields   : {dict(nulls) or 'none'}")
    print(f"  empty fields  : {dict(empty) or 'none'}")

    hard_nulls = {
        field: count
        for field, count in nulls.items()
        if field not in {"injection_type", "action_target_bbox"}
    }
    if missing or hard_nulls or empty:
        blockers.append("schema has missing, empty, or unexpected null fields")


def validate_labels(rows: list[dict[str, Any]], blockers: list[str]) -> None:
    print("\nLabels")
    for field, label_map in LABEL_MAPS.items():
        counts = Counter(row.get(field) for row in rows)
        unknown = sorted(set(counts) - set(label_map))
        print(f"  {field}: {dict(counts.most_common())}")
        if unknown:
            print(f"    unknown: {unknown}")
            blockers.append(f"{field} contains unknown labels")


def validate_leakage(splits: dict[str, list[dict[str, Any]]], blockers: list[str]) -> None:
    task_ids = [row["task_id"] for rows in splits.values() for row in rows]
    original_sets = {
        split_name: {row["original_task_id"] for row in rows}
        for split_name, rows in splits.items()
    }
    overlaps = {
        "train_val": len(original_sets["train"] & original_sets["val"]),
        "train_test": len(original_sets["train"] & original_sets["test"]),
        "val_test": len(original_sets["val"] & original_sets["test"]),
    }

    print("\nIDs and leakage")
    print(f"  task_id unique: {len(set(task_ids))}/{len(task_ids)}")
    print(f"  original_task_ids: { {k: len(v) for k, v in original_sets.items()} }")
    print(f"  split overlaps: {overlaps}")

    if len(task_ids) != len(set(task_ids)):
        blockers.append("duplicate task_id values")
    if any(overlaps.values()):
        blockers.append("original_task_id leakage between train/val/test")


def validate_images(
    rows: list[dict[str, Any]],
    base_dir: Path,
    image_sample: int,
    blockers: list[str],
    warnings: list[str],
) -> None:
    missing_refs = []
    all_paths = set()
    same_before_after = 0

    for idx, row in enumerate(rows):
        before = row.get("state_before")
        after = row.get("state_after")
        if before == after:
            same_before_after += 1
        for side in ("state_before", "state_after"):
            rel = row.get(side)
            if rel:
                all_paths.add(rel)
            if not rel or not (base_dir / rel).is_file():
                missing_refs.append((idx, side, rel))

    print("\nImages")
    print(f"  image refs checked: {len(rows) * 2:,}")
    print(f"  unique image paths: {len(all_paths):,}")
    print(f"  missing refs      : {len(missing_refs):,}")
    print(f"  same before/after : {same_before_after:,} ({pct(same_before_after, len(rows))})")

    if missing_refs:
        print(f"  examples: {missing_refs[:5]}")
        blockers.append("missing image references")

    borrowed = sum(1 for row in rows if row.get("borrowed_image"))
    if borrowed:
        warnings.append(
            f"{borrowed:,} rows ({pct(borrowed, len(rows))}) use borrowed images; "
            "exclude or report separately for visual-heavy evaluation"
        )

    if image_sample <= 0 or missing_refs:
        return

    rng = random.Random(42)
    selected = set()
    sorted_paths = sorted(all_paths)
    selected.update(sorted_paths[:3])
    selected.update(sorted_paths[-3:])
    if len(sorted_paths) > image_sample:
        selected.update(rng.sample(sorted_paths, image_sample))
    else:
        selected.update(sorted_paths)

    bad = []
    dims = Counter()
    sizes = []
    for rel in sorted(selected):
        path = base_dir / rel
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image = image.convert("RGB")
                dims[image.size] += 1
                sizes.append(path.stat().st_size)
                _ = image.resize((224, 224)).tobytes()[:16]
        except Exception as exc:  # noqa: BLE001 - report any decoder failure.
            bad.append((rel, repr(exc)))

    print(f"  opened sample    : {len(selected):,}")
    print(f"  bad sample images: {len(bad):,}")
    print(f"  top dimensions   : {dims.most_common(5)}")
    if sizes:
        print(
            "  sample size KB   : "
            f"min={min(sizes) / 1024:.2f}, "
            f"median={median(sizes) / 1024:.2f}, "
            f"mean={mean(sizes) / 1024:.2f}, "
            f"max={max(sizes) / 1024:.2f}"
        )

    if bad:
        print(f"  bad examples: {bad[:5]}")
        blockers.append("image decode failures in sample")


def validate_numeric_and_bbox(rows: list[dict[str, Any]], blockers: list[str], warnings: list[str]) -> None:
    print("\nNumeric values and bbox")

    for field in NUMERIC_0_1_FIELDS:
        values = []
        invalid = 0
        for row in rows:
            value = row.get(field)
            if isinstance(value, (int, float)) and 0 <= float(value) <= 1:
                values.append(float(value))
            else:
                invalid += 1
        if values:
            print(
                f"  {field}: invalid={invalid:,}, "
                f"min={min(values):.4f}, max={max(values):.4f}, mean={mean(values):.4f}"
            )
        if invalid:
            blockers.append(f"{field} contains invalid values")

    coord_bad = 0
    bbox_missing = 0
    bbox_bad = 0
    for row in rows:
        coords = row.get("action_coordinates")
        if not (
            isinstance(coords, list)
            and len(coords) == 2
            and all(isinstance(value, (int, float)) for value in coords)
        ):
            coord_bad += 1

        bbox = row.get("action_target_bbox")
        if bbox is None:
            bbox_missing += 1
        elif not (
            isinstance(bbox, dict)
            and all(key in bbox for key in ("x", "y", "width", "height"))
            and all(isinstance(bbox[key], (int, float)) for key in ("x", "y", "width", "height"))
            and bbox["width"] >= 0
            and bbox["height"] >= 0
        ):
            bbox_bad += 1

    print(f"  action_coordinates bad: {coord_bad:,}")
    print(f"  bbox missing          : {bbox_missing:,} ({pct(bbox_missing, len(rows))})")
    print(f"  bbox bad              : {bbox_bad:,}")

    if coord_bad:
        blockers.append("bad action_coordinates values")
    if bbox_bad:
        blockers.append("bad bbox values")
    if bbox_missing:
        warnings.append(
            f"{bbox_missing:,} rows ({pct(bbox_missing, len(rows))}) lack bbox; "
            "use a bbox_mask and exclude those rows from bbox loss"
        )


def validate_logic(rows: list[dict[str, Any]], blockers: list[str]) -> None:
    checks = {
        "failure_not_augmented": sum(
            1 for row in rows if row["execution_outcome"] == "FAILURE" and not row["is_augmented"]
        ),
        "success_augmented": sum(
            1 for row in rows if row["execution_outcome"] == "SUCCESS" and row["is_augmented"]
        ),
        "success_failure_type_not_none": sum(
            1 for row in rows if row["execution_outcome"] == "SUCCESS" and row["failure_type"] != "NONE"
        ),
        "failure_failure_type_none": sum(
            1 for row in rows if row["execution_outcome"] == "FAILURE" and row["failure_type"] == "NONE"
        ),
        "success_recovery_not_none": sum(
            1 for row in rows if row["execution_outcome"] == "SUCCESS" and row["recovery_strategy"] != "NONE"
        ),
        "failure_recovery_none": sum(
            1 for row in rows if row["execution_outcome"] == "FAILURE" and row["recovery_strategy"] == "NONE"
        ),
    }
    print("\nCross-field logic")
    print(f"  inconsistencies: {checks}")
    if any(checks.values()):
        blockers.append("cross-field logic inconsistencies")


def validate_label_leakage(rows: list[dict[str, Any]], research_blockers: list[str], warnings: list[str]) -> None:
    """Find shortcut labels that make multimodal learning claims invalid."""
    print("\nLeakage audit")

    for field in ("agent_confidence_before", "failure_confidence", "visual_diff_score"):
        success_vals = [row[field] for row in rows if row["execution_outcome"] == "SUCCESS"]
        failure_vals = [row[field] for row in rows if row["execution_outcome"] == "FAILURE"]
        success_range = (min(success_vals), max(success_vals))
        failure_range = (min(failure_vals), max(failure_vals))
        success_high_disjoint = max(failure_vals) < min(success_vals)
        failure_high_disjoint = max(success_vals) < min(failure_vals)

        print(
            f"  {field}: "
            f"SUCCESS [{success_range[0]:.4f}, {success_range[1]:.4f}], "
            f"FAILURE [{failure_range[0]:.4f}, {failure_range[1]:.4f}]"
        )
        if success_high_disjoint or failure_high_disjoint:
            research_blockers.append(
                f"{field} perfectly separates SUCCESS and FAILURE; do not use it as an input "
                "for outcome/failure detection"
            )

    deterministic_checks = {
        "execution_outcome == f(is_augmented)": sum(
            1 for row in rows if (row["execution_outcome"] == "FAILURE") == bool(row["is_augmented"])
        ),
        "memory_update_flag == is_augmented": sum(
            1 for row in rows if bool(row["memory_update_flag"]) == bool(row["is_augmented"])
        ),
        "failure_type NONE == injection_type None": sum(
            1 for row in rows if (row["failure_type"] == "NONE") == (row.get("injection_type") is None)
        ),
        "recovery_strategy NONE == injection_type None": sum(
            1 for row in rows if (row["recovery_strategy"] == "NONE") == (row.get("injection_type") is None)
        ),
    }
    print("  deterministic relations:")
    for name, count in deterministic_checks.items():
        rate = count / max(1, len(rows))
        print(f"    {name}: {count:,}/{len(rows):,} ({rate:.2%})")
        if rate == 1.0:
            research_blockers.append(f"{name} is deterministic")

    for target in ("failure_type", "recovery_strategy", "memory_update_flag", "execution_outcome"):
        grouped: dict[str, Counter] = {}
        for row in rows:
            grouped.setdefault(str(row.get("injection_type")), Counter())[row[target]] += 1

        pure_groups = sum(1 for counts in grouped.values() if len(counts) == 1)
        print(f"  injection_type -> {target}: {pure_groups}/{len(grouped)} pure groups")
        if target == "failure_type" and pure_groups == len(grouped):
            research_blockers.append(
                "failure_type is a deterministic function of injection_type; it is not an independently observed label"
            )
        elif pure_groups == len(grouped):
            warnings.append(f"{target} is deterministic from injection_type")

    by_desc: dict[str, Counter] = {}
    for row in rows:
        by_desc.setdefault(row["action_target_desc"], Counter())[row["action_type"]] += 1
    pure_desc = sum(1 for counts in by_desc.values() if len(counts) == 1)
    print(f"  action_target_desc -> action_type: {pure_desc:,}/{len(by_desc):,} pure descriptions")
    if pure_desc == len(by_desc):
        warnings.append(
            "action_target_desc perfectly determines action_type; do not include it as input "
            "when training/evaluating the action_type head"
        )


def smoke_batch(rows: list[dict[str, Any]], base_dir: Path, batch_size: int, blockers: list[str]) -> None:
    if batch_size <= 0:
        return

    rng = random.Random(42)
    sample = rng.sample(rows, min(batch_size, len(rows)))
    before_images = []
    after_images = []
    texts = []
    labels = {
        "execution_outcome": [],
        "failure_type": [],
        "action_type": [],
        "recovery_strategy": [],
    }
    bboxes = []
    bbox_masks = []
    confidences = []

    for row in sample:
        for field, store in (("state_before", before_images), ("state_after", after_images)):
            with Image.open(base_dir / row[field]) as image:
                image = image.convert("RGB").resize((224, 224))
                store.append(np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0)

        texts.append(
            f"Task: {row['task_description']} "
            f"Action: {row['action_type']} Target: {row['action_target_desc']}"
        )
        for field, label_map in LABEL_MAPS.items():
            labels[field].append(label_map[row[field]])

        bbox = row.get("action_target_bbox")
        if bbox:
            bboxes.append(
                [
                    bbox["x"] / 1280.0,
                    bbox["y"] / 720.0,
                    bbox["width"] / 1280.0,
                    bbox["height"] / 720.0,
                ]
            )
            bbox_masks.append(1.0)
        else:
            bboxes.append([0.0, 0.0, 0.0, 0.0])
            bbox_masks.append(0.0)
        confidences.append([row["failure_confidence"], row["agent_confidence_before"]])

    batch = {
        "before_image": np.stack(before_images).astype(np.float32),
        "after_image": np.stack(after_images).astype(np.float32),
        "bbox": np.asarray(bboxes, dtype=np.float32),
        "bbox_mask": np.asarray(bbox_masks, dtype=np.float32),
        "confidence": np.asarray(confidences, dtype=np.float32),
    }
    for field, values in labels.items():
        batch[field] = np.asarray(values, dtype=np.int64)

    all_finite = all(
        np.isfinite(value).all()
        for value in batch.values()
        if np.issubdtype(value.dtype, np.floating)
    )

    print("\nBatch smoke test")
    print(f"  text samples: {len(texts)}")
    print(f"  sample text : {texts[0][:180] if texts else ''}")
    print(f"  shapes      : { {key: value.shape for key, value in batch.items()} }")
    print(f"  dtypes      : { {key: str(value.dtype) for key, value in batch.items()} }")
    print(f"  finite floats: {all_finite}")
    print(
        "  image range : "
        f"before=({batch['before_image'].min():.3f}, {batch['before_image'].max():.3f}), "
        f"after=({batch['after_image'].min():.3f}, {batch['after_image'].max():.3f})"
    )

    if not all_finite:
        blockers.append("batch smoke test found non-finite values")


def print_split_summary(splits: dict[str, list[dict[str, Any]]]) -> None:
    print("\nSplit summary")
    for split_name, rows in splits.items():
        print(f"  {split_name}:")
        print(f"    rows      : {len(rows):,}")
        print(f"    tasks     : {len({row['original_task_id'] for row in rows}):,}")
        print(f"    websites  : {len({row['website_domain'] for row in rows}):,}")
        print(f"    outcome   : {dict(Counter(row['execution_outcome'] for row in rows).most_common())}")
        print(f"    failure   : {dict(Counter(row['failure_type'] for row in rows).most_common())}")
        print(f"    action    : {dict(Counter(row['action_type'] for row in rows).most_common())}")
        print(f"    borrowed  : {dict(Counter(row['borrowed_image'] for row in rows).most_common())}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final dataset trainability.")
    parser.add_argument("--base-dir", type=Path, default=BASE_DIR)
    parser.add_argument("--image-sample", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    print("=" * 78)
    print("FINAL DATASET TRAINABILITY CHECK")
    print("=" * 78)
    print(f"base_dir: {args.base_dir}")

    blockers: list[str] = []
    warnings: list[str] = []
    research_blockers: list[str] = []

    try:
        splits = load_splits(args.base_dir)
    except Exception as exc:  # noqa: BLE001 - top-level checker should report cleanly.
        print(f"\nBLOCKER: failed to load splits: {exc}")
        return 1

    rows = [row for split_rows in splits.values() for row in split_rows]
    print(f"total rows: {len(rows):,}")
    print(f"rows by split: { {name: len(split_rows) for name, split_rows in splits.items()} }")

    validate_schema(rows, blockers)
    validate_labels(rows, blockers)
    validate_leakage(splits, blockers)
    validate_images(rows, args.base_dir, args.image_sample, blockers, warnings)
    validate_numeric_and_bbox(rows, blockers, warnings)
    validate_logic(rows, blockers)
    validate_label_leakage(rows, research_blockers, warnings)
    smoke_batch(rows, args.base_dir, args.batch_size, blockers)
    print_split_summary(splits)

    print("\nTraining notes")
    print("  - Use bbox_mask for bbox regression loss.")
    print("  - For visual eval, report results with borrowed_image rows excluded or separated.")
    print("  - Treat recovery_success, confidence, and visual_diff_score as heuristic labels.")

    print("\nWarnings")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  none")

    print("\nVerdict")
    if blockers:
        for blocker in blockers:
            print(f"  BLOCKER: {blocker}")
        print("  NOT TRAINABLE until blockers are fixed.")
        return 1

    print("  MECHANICALLY TRAINABLE: final split files pass schema, label, image, split, and batch checks.")
    if research_blockers:
        print("  RESEARCH CLAIM BLOCKERS:")
        for blocker in research_blockers:
            print(f"    - {blocker}")
        print(
            "  Do not claim screenshot-only/multimodal failure detection from these leaked labels "
            "until the leakage is removed or controlled by ablation."
        )
    else:
        print("  No obvious shortcut leakage found by this checker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
