"""Generate lightweight review artifacts for gold dataset labels."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Iterable, List

from .gold_schema import GoldStep


def load_gold_steps(audit_path: str | Path) -> List[GoldStep]:
    path = Path(audit_path)
    steps: List[GoldStep] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                steps.append(GoldStep(**json.loads(line)))
    return steps


def select_review_queue(steps: Iterable[GoldStep], limit: int = 500) -> List[GoldStep]:
    selected: List[GoldStep] = []
    seen = set()

    def add(step: GoldStep) -> None:
        if step.sample_id not in seen and len(selected) < limit:
            selected.append(step)
            seen.add(step.sample_id)

    for step in steps:
        if step.failure_type_fine in {"unknown", "tool_failure", "state_no_change"}:
            add(step)
    for step in steps:
        if step.outcome_label == "FAILURE":
            add(step)
    for step in steps:
        add(step)
    return selected


def write_review_queue(audit_path: str | Path, output_path: str | Path, limit: int = 500) -> Path:
    steps = select_review_queue(load_gold_steps(audit_path), limit=limit)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for step in steps:
            f.write(json.dumps(step.model_dump(), ensure_ascii=False) + "\n")
    return out


def write_review_html(
    audit_path: str | Path,
    output_path: str | Path,
    image_base: str = ".",
    limit: int = 200,
) -> Path:
    steps = select_review_queue(load_gold_steps(audit_path), limit=limit)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for step in steps:
        before = html.escape(f"{image_base}/{step.state_before}".replace("\\", "/"))
        after = html.escape(f"{image_base}/{step.state_after}".replace("\\", "/"))
        rows.append(
            f"""
            <section class="sample">
              <h2>{html.escape(step.sample_id)}</h2>
              <p><strong>Task:</strong> {html.escape(step.task_description)}</p>
              <p><strong>Action:</strong> {html.escape(step.action_type)} -
                 {html.escape(step.action_target_desc)}</p>
              <p><strong>Auto label:</strong> outcome={html.escape(step.outcome_label)},
                 coarse={html.escape(str(step.failure_type_4))},
                 fine={html.escape(step.failure_type_fine)},
                 recovery={html.escape(step.recovery_strategy_observed)}</p>
              <div class="images">
                <figure><img src="{before}"><figcaption>Before</figcaption></figure>
                <figure><img src="{after}"><figcaption>After</figcaption></figure>
              </div>
              <p><strong>Notes:</strong> {html.escape(step.metadata.get("auto_label_reason", ""))}</p>
            </section>
            """
        )

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Gold Dataset Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #222; }}
    .sample {{ background: white; border: 1px solid #ddd; padding: 16px; margin-bottom: 18px; }}
    .images {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    img {{ max-width: 100%; border: 1px solid #bbb; }}
    figcaption {{ font-size: 13px; color: #555; }}
  </style>
</head>
<body>
  <h1>Gold Dataset Review Queue</h1>
  <p>Review labels manually, then write corrections back to the audit JSONL.</p>
  {''.join(rows)}
</body>
</html>
"""
    out.write_text(page, encoding="utf-8")
    return out
