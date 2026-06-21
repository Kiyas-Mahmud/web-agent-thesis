"""Repair empty/broken state_before and state_after image paths.

Never removes steps. Tries 3 strategies in order:
  1. Find the image on disk using task_id-based patterns.
  2. Borrow from the same trajectory (state_after of step N-1 == state_before of step N).
  3. Generate a 256x256 grey placeholder and flag the step.

Output preserves every input record (same size).

Usage:
    python repair_image_paths.py <input_json> <images_dir>
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PLACEHOLDER_NAME = "_missing_placeholder.jpg"


def is_empty(v) -> bool:
    return v is None or str(v).strip() == ""


def split_base_and_step(task_id: str) -> tuple[str, int]:
    base, _, step = task_id.rpartition("_")
    return base, int(step)


def ensure_placeholder(images_dir: Path) -> str:
    path = images_dir / PLACEHOLDER_NAME
    if not path.exists():
        img = Image.new("RGB", (256, 256), color=(160, 160, 160))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except OSError:
            font = ImageFont.load_default()
        draw.text((28, 118), "missing screenshot", fill=(30, 30, 30), font=font)
        img.save(path, "JPEG", quality=85)
    return str(Path("images") / PLACEHOLDER_NAME).replace("/", os.sep)


def find_on_disk(images_dir: Path, base: str, step: int, side: str) -> str | None:
    """Strategy 1: look for the file on disk under several plausible names."""
    traj_dir = images_dir / base
    if not traj_dir.is_dir():
        return None
    candidates = [
        f"step_{step:04d}_{side}.jpg",
        f"step_{step:04d}_{side}.png",
        f"step_{step}_{side}.jpg",
        f"step_{step}_{side}.png",
    ]
    for name in candidates:
        if (traj_dir / name).is_file():
            return str(Path("images") / base / name).replace("/", os.sep)
    return None


def build_trajectory_index(data: list[dict]) -> dict[str, dict[int, dict]]:
    """Map base task_id -> {step_index: record} for borrow lookups."""
    index: dict[str, dict[int, dict]] = defaultdict(dict)
    for rec in data:
        tid = rec.get("task_id")
        if not tid or "_" not in tid:
            continue
        try:
            base, step = split_base_and_step(tid)
        except ValueError:
            continue
        index[base][step] = rec
    return index


def repair(input_path: str, images_dir: str) -> dict:
    in_path = Path(input_path)
    images_root = Path(images_dir)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    placeholder_rel = ensure_placeholder(images_root)
    traj = build_trajectory_index(data)

    stats = {
        "total": len(data),
        "before_broken": 0,
        "after_broken": 0,
        "fixed_on_disk": 0,
        "fixed_borrow": 0,
        "fixed_placeholder": 0,
        "flagged_borrowed": 0,
        "flagged_placeholder": 0,
    }

    for rec in data:
        tid = rec.get("task_id")
        if not tid or "_" not in tid:
            continue
        try:
            base, step = split_base_and_step(tid)
        except ValueError:
            continue

        for side, neighbor_side, neighbor_offset in (
            ("before", "after", -1),
            ("after", "before", +1),
        ):
            field = f"state_{side}"
            if not is_empty(rec.get(field)):
                continue
            stats[f"{side}_broken"] += 1

            # Strategy 1: find the file on disk.
            found = find_on_disk(images_root, base, step, side)
            if found:
                rec[field] = found
                stats["fixed_on_disk"] += 1
                continue

            # Strategy 2: borrow from a neighbor step in the same trajectory.
            neighbor = traj.get(base, {}).get(step + neighbor_offset)
            if neighbor:
                borrow_field = f"state_{neighbor_side}"
                borrow_val = neighbor.get(borrow_field)
                if not is_empty(borrow_val):
                    rec[field] = borrow_val
                    rec["borrowed_image"] = True
                    stats["fixed_borrow"] += 1
                    stats["flagged_borrowed"] += 1
                    continue
            # Also try same-step opposite side as a last borrow attempt.
            same_opposite = rec.get(f"state_{neighbor_side}")
            if not is_empty(same_opposite):
                rec[field] = same_opposite
                rec["borrowed_image"] = True
                stats["fixed_borrow"] += 1
                stats["flagged_borrowed"] += 1
                continue

            # Strategy 3: placeholder.
            rec[field] = placeholder_rel
            rec["placeholder_image"] = True
            stats["fixed_placeholder"] += 1
            stats["flagged_placeholder"] += 1

    out_path = in_path.with_name(in_path.stem + "_REPAIRED.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    stats["output_path"] = str(out_path)
    stats["output_records"] = len(data)
    return stats


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    stats = repair(sys.argv[1], sys.argv[2])

    print("Repair summary")
    print("-" * 40)
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Verify: no empties left.
    with open(stats["output_path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    eb = sum(1 for r in data if is_empty(r.get("state_before")))
    ea = sum(1 for r in data if is_empty(r.get("state_after")))
    print("-" * 40)
    print(f"  verify empty_before: {eb}")
    print(f"  verify empty_after : {ea}")
    print(f"  verify size        : {len(data)} (expected {stats['total']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
