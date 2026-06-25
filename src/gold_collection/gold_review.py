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
        expected = html.escape(str(step.metadata.get("expected_fine_failure", "")))
        error = html.escape(str(step.error_message or ""))
        url_before = html.escape(str(step.url_before or ""))
        url_after = html.escape(str(step.url_after or ""))
        pixel_diff = "" if step.pixel_diff is None else f"{step.pixel_diff:.6f}"
        ssim = "" if step.ssim is None else f"{step.ssim:.6f}"
        label_source = html.escape(step.label_source)
        explanation = html.escape(step.metadata.get("auto_label_reason", ""))
        if step.failure_type_fine == "perception_error" and step.pixel_diff == 0:
            explanation = (
                explanation
                + " Review note: unchanged before/after can be correct when the target "
                "selector was absent and the browser action was a no-op."
            )
        rows.append(
            f"""
            <section class="sample">
              <h2>{html.escape(step.sample_id)}</h2>
              <div class="meta-grid">
                <p><strong>Task</strong><br>{html.escape(step.task_description)}</p>
                <p><strong>Action</strong><br>{html.escape(step.action_type)} - {html.escape(step.action_target_desc)}</p>
                <p><strong>Label</strong><br>outcome={html.escape(step.outcome_label)}, coarse={html.escape(str(step.failure_type_4))}, fine={html.escape(step.failure_type_fine)}</p>
                <p><strong>Source</strong><br>{label_source}, expected={expected}, recovery={html.escape(step.recovery_strategy_observed)}</p>
                <p><strong>URL Before</strong><br><span class="mono">{url_before}</span></p>
                <p><strong>URL After</strong><br><span class="mono">{url_after}</span></p>
                <p><strong>Error</strong><br><span class="mono">{error}</span></p>
                <p><strong>Visual Metrics</strong><br>pixel_diff={html.escape(pixel_diff)}, ssim={html.escape(ssim)}</p>
              </div>
              <div class="images">
                <figure><a href="{before}" target="_blank"><img src="{before}"></a><figcaption>Before - click image for full size</figcaption></figure>
                <figure><a href="{after}" target="_blank"><img src="{after}"></a><figcaption>After - click image for full size</figcaption></figure>
              </div>
              <p><strong>Review evidence:</strong> {explanation}</p>
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
    .meta-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 18px; }}
    .meta-grid p {{ margin: 4px 0; line-height: 1.35; }}
    .mono {{ font-family: Consolas, Monaco, monospace; font-size: 13px; word-break: break-all; }}
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
