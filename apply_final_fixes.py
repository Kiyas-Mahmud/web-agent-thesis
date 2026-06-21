"""Apply 3 deterministic fixes to augmented_trajectories_READY_REPAIRED.json.

Never removes or reorders records. Output: FINAL_Trajectories_Update.json
  Fix 1: backslashes -> forward slashes in state_before, state_after
  Fix 2: enrich action_target_desc values starting with "element_"
  Fix 3: add borrowed_image=false where the field is missing
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


SRC = Path("output/dataset_70k_safe/augmented_trajectories_READY_REPAIRED.json")
DST = Path("output/dataset_70k_safe/FINAL_Trajectories_Update.json")
EXPECTED = 70965


def enrich_target_desc(rec: dict) -> str | None:
    action = rec.get("action_type")
    bbox = rec.get("action_target_bbox")
    coords = rec.get("action_coordinates") or [0, 0]
    x, y = int(coords[0]), int(coords[1])

    if action == "TYPE":
        return "text input field"
    if action == "SELECT":
        return "dropdown selector"
    if action == "CLICK":
        w = h = None
        if isinstance(bbox, dict):
            w = bbox.get("width", bbox.get("w"))
            h = bbox.get("height", bbox.get("h"))
        elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        if w is not None and h is not None:
            if w > 200 and h > 40:
                return "large button or link"
            if w < 50 and h < 50:
                return "small icon or checkbox"
        return f"clickable element at ({x}, {y})"
    return None


def main() -> int:
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == EXPECTED, f"expected {EXPECTED} records, got {len(data)}"

    stats = {
        "paths_fixed": 0,
        "desc_enriched": 0,
        "borrowed_added": 0,
    }

    samples_before: list[dict] = [copy.deepcopy(r) for r in data[:3]]

    for rec in data:
        # Fix 1 — paths
        for field in ("state_before", "state_after"):
            v = rec.get(field)
            if isinstance(v, str) and "\\" in v:
                rec[field] = v.replace("\\", "/")
                stats["paths_fixed"] += 1

        # Fix 2 — enrich generic action_target_desc
        desc = rec.get("action_target_desc")
        if isinstance(desc, str) and desc.startswith("element_"):
            new_desc = enrich_target_desc(rec)
            if new_desc is not None:
                rec["action_target_desc"] = new_desc
                stats["desc_enriched"] += 1

        # Fix 3 — normalize borrowed_image
        if "borrowed_image" not in rec:
            rec["borrowed_image"] = False
            stats["borrowed_added"] += 1

    samples_after = data[:3]

    assert len(data) == EXPECTED, f"record count changed: {len(data)}"

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print("=" * 60)
    print("FINAL FIX REPORT")
    print("=" * 60)
    print(f"Input:  {SRC}")
    print(f"Output: {DST}")
    print(f"Total records written : {len(data)}")
    print(f"Paths fixed (\\ -> /) : {stats['paths_fixed']}")
    print(f"action_target_desc enriched : {stats['desc_enriched']}")
    print(f"borrowed_image=false added  : {stats['borrowed_added']}")
    print()
    print("-" * 60)
    print("SAMPLE RECORDS (before -> after)")
    print("-" * 60)
    for i, (b, a) in enumerate(zip(samples_before, samples_after), 1):
        print(f"\n[Record {i}] task_id={a.get('task_id')}")
        print(f"  state_before:")
        print(f"    before: {b.get('state_before')}")
        print(f"    after : {a.get('state_before')}")
        print(f"  state_after:")
        print(f"    before: {b.get('state_after')}")
        print(f"    after : {a.get('state_after')}")
        print(f"  action_target_desc:")
        print(f"    before: {b.get('action_target_desc')}")
        print(f"    after : {a.get('action_target_desc')}")
        print(f"  borrowed_image:")
        print(f"    before: {'<missing>' if 'borrowed_image' not in b else b['borrowed_image']}")
        print(f"    after : {a.get('borrowed_image')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
