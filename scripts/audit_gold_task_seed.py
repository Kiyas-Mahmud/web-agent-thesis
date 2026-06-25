"""Audit gold ActionLog seeds before browser collection.

The goal is to catch cheap text/action shortcuts before spending time on
Playwright collection. A seed is only safe enough for collection if repeated
model-visible groups contain both success and failure examples.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LEAK_KEYWORDS = re.compile(
    r"missing|non[- ]?existent|not found|does not exist|perception failure|failure|failed",
    re.IGNORECASE,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def expected_label(value: Any) -> str:
    value = str(value or "").lower()
    if value in {"success", "none"}:
        return "SUCCESS"
    if value:
        return "FAILURE"
    return "UNKNOWN"


def first_action(row: dict[str, Any]) -> dict[str, Any]:
    actions = row.get("actions") or []
    return actions[0] if actions and isinstance(actions[0], dict) else {}


def expected_for_step(row: dict[str, Any], step_index: int) -> Any:
    metadata = row.get("metadata") or {}
    values = metadata.get("expected_step_behaviors")
    if isinstance(values, list) and step_index < len(values):
        return values[step_index]
    return metadata.get("expected_behavior")


def iter_seed_steps(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded = []
    for row in rows:
        actions = row.get("actions") or []
        for step_index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            expanded.append(
                {
                    "task_id": row.get("task_id"),
                    "task_description": row.get("task_description"),
                    "domain": (row.get("metadata") or {}).get("domain", ""),
                    "intent": (row.get("metadata") or {}).get("intent", ""),
                    "expected": expected_for_step(row, step_index),
                    "action": action,
                }
            )
    return expanded


def model_visible_text(row: dict[str, Any]) -> str:
    action = row["action"]
    return " ".join(
        str(value or "")
        for value in (
            row.get("task_description"),
            action.get("description") or action.get("target"),
            action.get("action_type"),
        )
    )


def group_counts(
    rows: list[dict[str, Any]],
    key_name: str,
    key_fn,
) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[str(key_fn(row))][expected_label(row.get("expected"))] += 1
    return dict(counts)


def print_group_report(name: str, counts: dict[str, Counter[str]], blockers: list[str]) -> None:
    print(name)
    one_sided = {}
    for key, counter in sorted(counts.items()):
        total = sum(counter.values())
        if total >= 2 and len([label for label, count in counter.items() if count]) == 1:
            one_sided[key] = dict(counter)
    print(f"  groups: {len(counts)}")
    print(f"  one_sided_repeated: {one_sided}")
    if one_sided:
        blockers.append(f"{name} has repeated one-sided groups")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit gold ActionLog seed balance.")
    parser.add_argument("--log-file", type=Path, required=True)
    parser.add_argument("--fail-on-blockers", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_rows = load_jsonl(args.log_file)
    rows = iter_seed_steps(task_rows)
    blockers: list[str] = []

    print("Seed")
    print(f"  file: {args.log_file}")
    print(f"  tasks: {len(task_rows)}")
    print(f"  steps: {len(rows)}")

    labels = Counter(expected_label(row.get("expected")) for row in rows)
    fine = Counter(str(row.get("expected") or "UNKNOWN") for row in rows)
    print("Labels")
    print(f"  expected: {dict(labels.most_common())}")
    print(f"  fine_expected: {dict(fine.most_common())}")
    if labels.get("UNKNOWN"):
        blockers.append("some rows are missing metadata.expected_behavior")
    if not labels.get("SUCCESS") or not labels.get("FAILURE"):
        blockers.append("seed must contain both success and failure examples")

    action_types = Counter(str(row["action"].get("action_type") or "") for row in rows)
    print("Actions")
    print(f"  action_type: {dict(action_types.most_common())}")

    keyword_hits = [
        row.get("task_id")
        for row in rows
        if LEAK_KEYWORDS.search(model_visible_text(row))
    ]
    print("Explicit Leak Keywords")
    print(f"  hits: {keyword_hits}")
    if keyword_hits:
        blockers.append("model-visible task/action text contains explicit leak keywords")

    print_group_report(
        "Intent Balance",
        group_counts(rows, "intent", lambda row: row.get("intent", "")),
        blockers,
    )
    print_group_report(
        "Domain Balance",
        group_counts(rows, "domain", lambda row: row.get("domain", "")),
        blockers,
    )
    print_group_report(
        "Task Text Balance",
        group_counts(rows, "task_description", lambda row: row.get("task_description", "")),
        blockers,
    )
    print_group_report(
        "Action Text Balance",
        group_counts(
            rows,
            "action_text",
            lambda row: row["action"].get("description")
            or row["action"].get("target")
            or "",
        ),
        blockers,
    )
    print_group_report(
        "Action Type Balance",
        group_counts(rows, "action_type", lambda row: row["action"].get("action_type", "")),
        blockers,
    )

    print("Verdict")
    if blockers:
        for blocker in blockers:
            print(f"  BLOCKER: {blocker}")
        return 1 if args.fail_on_blockers else 0
    print("  SEED PASSED PRE-COLLECTION LEAKAGE AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
