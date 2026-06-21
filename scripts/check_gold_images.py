"""Check gold dataset screenshots and before/after visual-change shortcuts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean_abs_diff(before_path: Path, after_path: Path) -> tuple[float, bool]:
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    diff = ImageChops.difference(before, after)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / 3 / 255.0, diff.getbbox() is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check gold dataset image integrity.")
    parser.add_argument("--base-dir", type=Path, required=True)
    parser.add_argument("--audit-file", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_file = args.audit_file or args.base_dir / "gold_audit.jsonl"
    rows = load_jsonl(audit_file)

    image_files = list((args.base_dir / "images").rglob("*.png"))
    bad_images = []
    blank_like = []
    small_images = []
    dimensions = Counter()

    for path in image_files:
        try:
            image = Image.open(path).convert("RGB")
            dimensions[image.size] += 1
            stat = ImageStat.Stat(image)
            variance = sum(stat.var) / 3
            if variance < 1.0:
                blank_like.append((str(path), variance))
            if image.width < 100 or image.height < 100:
                small_images.append((str(path), image.size))
        except Exception as exc:  # noqa: BLE001 - diagnostic script should report all.
            bad_images.append((str(path), str(exc)))

    print("Image Files")
    print(f"  png_count: {len(image_files)}")
    print(f"  bad_images: {len(bad_images)}")
    print(f"  blank_like: {len(blank_like)}")
    print(f"  small_images: {len(small_images)}")
    print(f"  dimensions: {dict(dimensions.most_common())}")

    diff_rows = []
    for row in rows:
        before = args.base_dir / row["state_before"]
        after = args.base_dir / row["state_after"]
        diff_value, changed = mean_abs_diff(before, after)
        diff_rows.append(
            {
                "sample_id": row["sample_id"],
                "outcome_label": row["outcome_label"],
                "failure_type_4": row["failure_type_4"],
                "diff": diff_value,
                "changed": changed,
            }
        )

    print("Visual Change")
    for label in ("SUCCESS", "FAILURE"):
        values = sorted(row["diff"] for row in diff_rows if row["outcome_label"] == label)
        no_change = sum(
            1 for row in diff_rows if row["outcome_label"] == label and not row["changed"]
        )
        if values:
            print(
                f"  {label}: n={len(values)}, min={values[0]:.6f}, "
                f"median={values[len(values)//2]:.6f}, max={values[-1]:.6f}, "
                f"no_change={no_change}"
            )

    best_accuracy = 0.0
    best_threshold = 0.0
    thresholds = sorted({row["diff"] for row in diff_rows})
    labels = [row["outcome_label"] for row in diff_rows]
    for threshold in thresholds:
        predictions = [
            "SUCCESS" if row["diff"] > threshold else "FAILURE" for row in diff_rows
        ]
        accuracy = sum(pred == label for pred, label in zip(predictions, labels)) / len(labels)
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
    print("Visual-Diff Shortcut Diagnostic")
    print(f"  same_data_best_accuracy: {best_accuracy:.4f}")
    print(f"  threshold: {best_threshold:.6f}")

    blockers = []
    if bad_images:
        blockers.append("some screenshots cannot be opened")
    if blank_like:
        blockers.append("some screenshots look blank")
    if small_images:
        blockers.append("some screenshots are unexpectedly small")
    if best_accuracy >= 0.90:
        blockers.append("before/after visual-change threshold is a strong shortcut")

    print("Verdict")
    if blockers:
        for blocker in blockers:
            print(f"  WARNING: {blocker}")
        return 0
    print("  IMAGE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
