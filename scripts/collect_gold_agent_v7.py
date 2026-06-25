"""Collect a small goal-only gold batch with an online browser agent.

This runner is intentionally separate from ``collect_gold_dataset.py`` because
that script replays fixed selectors. Here the seed contains only goals and
hidden review/oracle metadata. The agent chooses each action from the live page.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gold_collection.gold_schema import build_gold_step, normalize_recovery  # noqa: E402
from metric_computation import MetricComputer  # noqa: E402
from playwright.sync_api import Page, sync_playwright  # noqa: E402


STOPWORDS = {
    "a",
    "an",
    "and",
    "about",
    "for",
    "from",
    "go",
    "into",
    "link",
    "open",
    "page",
    "the",
    "to",
}

SYNONYMS = {
    "documentation": {"docs", "doc", "manual", "guide"},
    "docs": {"documentation", "doc", "manual", "guide"},
    "install": {"installation", "download", "setup"},
    "installation": {"install", "download", "setup"},
    "download": {"downloads", "install", "installation"},
    "community": {"communities", "forum", "forums"},
    "release": {"releases", "changelog", "notes", "highlights"},
    "information": {"info", "about", "learn"},
    "api": {"reference", "developer", "developers"},
    "support": {"help"},
    "blog": {"news", "updates"},
}


@dataclass
class Candidate:
    selector: str
    text: str
    href: str
    tag: str
    bbox: dict[str, float] | None
    score: float = 0.0


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    expanded: set[str] = set()
    for token in raw:
        if token in STOPWORDS or len(token) < 2:
            continue
        expanded.add(token)
        expanded.update(SYNONYMS.get(token, set()))
    return expanded


def host_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host


def rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def extract_candidates(page: Page) -> list[Candidate]:
    rows = page.evaluate(
        """
        () => {
          const selectors = [
            'a[href]', 'button', 'input', 'textarea', 'select',
            '[role="button"]', '[role="link"]'
          ];
          const seen = new Set();
          const out = [];
          for (const el of document.querySelectorAll(selectors.join(','))) {
            if (seen.has(el)) continue;
            seen.add(el);
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            if (!rect || rect.width < 4 || rect.height < 4) continue;
            if (style.visibility === 'hidden' || style.display === 'none') continue;
            if (rect.bottom < 0 || rect.right < 0) continue;
            if (rect.top > window.innerHeight || rect.left > window.innerWidth) continue;
            const i = out.length;
            el.setAttribute('data-gold-v7-candidate', String(i));
            const text = [
              el.innerText,
              el.getAttribute('aria-label'),
              el.getAttribute('title'),
              el.getAttribute('placeholder'),
              el.getAttribute('value'),
              el.getAttribute('href')
            ].filter(Boolean).join(' ').replace(/\\s+/g, ' ').trim();
            out.push({
              selector: `[data-gold-v7-candidate="${i}"]`,
              text,
              href: el.href || el.getAttribute('href') || '',
              tag: el.tagName.toLowerCase(),
              bbox: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
            });
          }
          return out.slice(0, 120);
        }
        """
    )
    return [
        Candidate(
            selector=str(row["selector"]),
            text=str(row.get("text") or ""),
            href=str(row.get("href") or ""),
            tag=str(row.get("tag") or ""),
            bbox=row.get("bbox"),
        )
        for row in rows
    ]


def inert_click_coordinates(page: Page) -> list[float]:
    try:
        point = page.evaluate(
            """
            () => {
              const xs = [32, 96, 180, 320, 500, 720, 980, 1180];
              const ys = [96, 160, 240, 340, 460, 600, 690];
              const interactive = 'a,button,input,textarea,select,[role="button"],[role="link"]';
              for (const y of ys) {
                for (const x of xs) {
                  const el = document.elementFromPoint(x, y);
                  if (!el) continue;
                  if (el.closest(interactive)) continue;
                  const rect = el.getBoundingClientRect();
                  if (!rect || rect.width < 8 || rect.height < 8) continue;
                  return [x, y];
                }
              }
              return [640, 360];
            }
            """
        )
        if isinstance(point, list) and len(point) == 2:
            return [float(point[0]), float(point[1])]
    except Exception:
        pass
    return [640.0, 360.0]


def score_candidate(goal: str, candidate: Candidate) -> float:
    goal_tokens = tokens(goal)
    cand_tokens = tokens(" ".join([candidate.text, candidate.href]))
    if not goal_tokens or not cand_tokens:
        return 0.0

    overlap = goal_tokens & cand_tokens
    score = float(len(overlap))
    text_lower = candidate.text.lower()
    href_lower = candidate.href.lower()
    for token in goal_tokens:
        if token in text_lower:
            score += 0.65
        if token in href_lower:
            score += 0.35
    if any(bad in text_lower for bad in ("login", "sign in", "donate", "register")):
        score -= 1.0
    if candidate.tag in {"input", "textarea"} and "search" not in goal.lower():
        score -= 0.7
    return score


def candidate_satisfies_oracle(candidate: Candidate, metadata: dict[str, Any]) -> bool:
    haystack = " ".join([candidate.text, candidate.href]).lower()
    url_checks = [str(value).lower() for value in metadata.get("success_url_contains") or []]
    text_checks = [str(value).lower() for value in metadata.get("success_text_contains") or []]
    return any(value in haystack for value in url_checks + text_checks)


def candidate_is_navigation(candidate: Candidate, current_url: str) -> bool:
    href = (candidate.href or "").strip()
    if not href:
        return False
    if href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
        return False
    return href.rstrip("/").lower() != (current_url or "").rstrip("/").lower()


def stable_bucket(value: str, modulo: int) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def choose_action(task: dict[str, Any], page: Page, step_index: int) -> dict[str, Any]:
    goal = str(task.get("task_description") or "")
    metadata = task.get("metadata") or {}
    policy = str(metadata.get("agent_policy") or "normal")
    if metadata.get("agent_intent") == "loop_probe":
        point = inert_click_coordinates(page)
        return {
            "kind": "body_click",
            "description": "Agent clicked the main page area",
            "coordinates": point,
        }
    if policy == "perception_probe":
        point = inert_click_coordinates(page)
        return {
            "kind": "body_click",
            "description": "Agent clicked the main page area",
            "coordinates": point,
        }

    if "scroll" in goal.lower():
        return {
            "kind": "scroll",
            "description": "Agent scrolled the page",
            "scroll_amount": int(metadata.get("scroll_amount") or 700),
        }

    candidates = extract_candidates(page)
    for candidate in candidates:
        candidate.score = score_candidate(goal, candidate)
    candidates.sort(key=lambda item: (-item.score, item.bbox["y"] if item.bbox else math.inf))

    if candidates and candidates[0].score >= 1.0:
        chosen = candidates[0]
        if policy == "distractor":
            current_url = page.url
            for candidate in candidates:
                if (
                    candidate_is_navigation(candidate, current_url)
                    and not candidate_satisfies_oracle(candidate, metadata)
                ):
                    chosen = candidate
                    break
            else:
                if len(candidates) > 1 and candidates[1].score >= 0.75:
                    chosen = candidates[1]
        elif (
            policy == "normal"
            and len(candidates) > 1
            and candidates[1].score >= 1.0
            and candidates[0].score - candidates[1].score <= 2.0
            and stable_bucket(str(task.get("task_id")), 9) == 0
        ):
            chosen = candidates[1]
        return {
            "kind": "click",
            "selector": chosen.selector,
            "description": f"Agent clicked {chosen.text[:120] or chosen.href[:120]}",
            "bbox": chosen.bbox,
            "candidate_text": chosen.text,
            "candidate_href": chosen.href,
            "candidate_score": chosen.score,
        }

    point = inert_click_coordinates(page)
    return {
        "kind": "body_click",
        "description": "Agent clicked the main page area",
        "coordinates": point,
    }


def execute_action(page: Page, action: dict[str, Any], timeout_ms: int) -> tuple[bool, str | None, float]:
    start = time.time()
    try:
        if action["kind"] == "click":
            page.locator(action["selector"]).first.click(timeout=timeout_ms)
        elif action["kind"] == "scroll":
            page.mouse.wheel(0, int(action.get("scroll_amount") or 700))
        else:
            x, y = action.get("coordinates") or [640, 360]
            page.mouse.click(float(x), float(y))
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(500)
        return True, None, (time.time() - start) * 1000
    except Exception as exc:  # noqa: BLE001 - keep browser failure in audit.
        return False, str(exc), (time.time() - start) * 1000


def page_contains(page: Page, needles: list[str]) -> bool:
    if not needles:
        return False
    try:
        text = page.locator("body").inner_text(timeout=1500).lower()
    except Exception:
        text = ""
    return any(needle.lower() in text for needle in needles)


def goal_satisfied(page: Page, url: str, metadata: dict[str, Any]) -> bool:
    url_checks = [str(value).lower() for value in metadata.get("success_url_contains") or []]
    text_checks = [str(value).lower() for value in metadata.get("success_text_contains") or []]
    lowered_url = (url or "").lower()
    if url_checks and any(value in lowered_url for value in url_checks):
        return True
    if text_checks and page_contains(page, text_checks):
        return True
    return False


def compute_metrics(metric_computer: MetricComputer, index: int, before: Path, after: Path, elapsed: float) -> dict[str, Any]:
    try:
        return metric_computer.compute_step_metrics(
            step_id=index,
            before_screenshot=before,
            after_screenshot=after,
            execution_time_ms=elapsed,
        ).to_dict()
    except Exception as exc:  # noqa: BLE001
        return {"visual": {}, "metric_error": str(exc)}


def visual_value(metrics: dict[str, Any], name: str) -> float | None:
    value = (metrics.get("visual") or {}).get(name)
    return float(value) if value is not None else None


def classify_step(
    *,
    success: bool,
    action_ok: bool,
    url_changed: bool,
    changed: bool,
    no_progress_seen: int,
    action: dict[str, Any],
) -> tuple[str, str, str]:
    if success:
        return "SUCCESS", "none", "NONE"
    if no_progress_seen >= 3:
        return "FAILURE", "loop_detected", "REPLAN"
    if action_ok and changed:
        recovery = "BACKTRACK" if url_changed else "ALTERNATIVE_TARGET"
        return "FAILURE", "action_mismatch", recovery
    return "FAILURE", "perception_error", "ALTERNATIVE_TARGET"


def collect_task(
    *,
    task: dict[str, Any],
    page: Page,
    output_dir: Path,
    metric_computer: MetricComputer,
    timeout_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    task_id = str(task["task_id"])
    metadata = task.get("metadata") or {}
    source_name = str(metadata.get("collection_type") or "agent_v7")
    max_steps = int(metadata.get("max_steps") or task.get("max_steps") or 3)
    image_dir = output_dir / "images" / task_id
    image_dir.mkdir(parents=True, exist_ok=True)
    trajectory_steps: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    no_progress_seen = 0

    page.goto(str(task["start_url"]), wait_until="domcontentloaded", timeout=timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    for step_index in range(max_steps):
        before_url = page.url
        before = image_dir / f"before_{step_index + 1:04d}.png"
        after = image_dir / f"after_{step_index + 1:04d}.png"
        page.screenshot(path=str(before), full_page=False)

        action = choose_action(task, page, step_index)
        action_ok, error, elapsed = execute_action(page, action, timeout_ms=timeout_ms)
        after_url = page.url
        page.screenshot(path=str(after), full_page=False)
        metrics = compute_metrics(metric_computer, step_index, before, after, elapsed)
        pixel_diff = visual_value(metrics, "pixel_diff_score")
        ssim = visual_value(metrics, "ssim_score")
        changed = bool(before_url != after_url or (pixel_diff is not None and pixel_diff >= 0.01))
        if changed:
            no_progress_seen = 0
        else:
            no_progress_seen += 1

        satisfied = goal_satisfied(page, after_url, metadata)
        outcome, fine, recovery = classify_step(
            success=satisfied,
            action_ok=action_ok,
            url_changed=before_url != after_url,
            changed=changed,
            no_progress_seen=no_progress_seen,
            action=action,
        )

        step_record = {
            "step_id": step_index,
            "action": action,
            "result": {
                "success": action_ok,
                "goal_satisfied": satisfied,
                "error": error,
                "execution_time_ms": elapsed,
            },
            "screenshot_before": str(before),
            "screenshot_after": str(after),
            "url_before": before_url,
            "url_after": after_url,
            "metrics": metrics,
        }
        trajectory_steps.append(step_record)

        gold_step = build_gold_step(
            task_id=task_id,
            step_index=step_index,
            source=source_name,
            website_domain=str(metadata.get("domain") or host_from_url(str(task["start_url"]))),
            task_description=str(task.get("task_description") or ""),
            state_before=rel(before, output_dir),
            state_after=rel(after, output_dir),
            action_type="CLICK" if action["kind"] in {"click", "body_click"} else "SCROLL",
            action_target_desc="Agent clicked page element",
            action_coordinates=action.get("coordinates"),
            action_target_bbox=action.get("bbox"),
            url_before=before_url,
            url_after=after_url,
            page_status="OK" if action_ok else "ACTION_ERROR",
            error_message=error,
            pixel_diff=pixel_diff,
            ssim=ssim,
            outcome_label=outcome,
            failure_type_fine=fine,
            recovery_strategy_observed=normalize_recovery(recovery),
            label_source="agent_v7_observed",
            review_status="pending",
            metadata={
                "auto_label_reason": (
                    f"Agent-run v7 label from goal_satisfied={satisfied}, "
                    f"changed={changed}, no_progress_seen={no_progress_seen}."
                ),
                "agent_action": action,
                "raw_action_target_desc": str(action.get("description") or ""),
                "action_target_desc_sanitized": True,
                "oracle": {
                    "success_url_contains": metadata.get("success_url_contains") or [],
                    "success_text_contains": metadata.get("success_text_contains") or [],
                },
            },
        )
        audit_this_step = not (
            metadata.get("agent_intent") == "loop_probe"
            and fine != "loop_detected"
        )
        if audit_this_step:
            audit_rows.append(gold_step.model_dump())

        if satisfied or fine in {"action_mismatch", "perception_error"} and metadata.get("agent_intent") != "loop_probe":
            break

    trajectory = {
        "task_id": task_id,
        "start_url": task["start_url"],
        "task_description": task.get("task_description") or "",
        "source": source_name,
        "metadata": metadata,
        "steps": trajectory_steps,
    }
    return audit_rows, trajectory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect v7 goal-only agent smoke gold data.")
    parser.add_argument("--task-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = load_jsonl(args.task_file)[: args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = args.output_dir / "gold_audit.jsonl"
    replay_dir = args.output_dir / "replays"
    replay_dir.mkdir(parents=True, exist_ok=True)
    if audit_path.exists():
        audit_path.unlink()

    metric_computer = MetricComputer(output_dir=str(args.output_dir))
    all_rows: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        for index, task in enumerate(tasks, start=1):
            print(f"[{index}/{len(tasks)}] {task['task_id']} {task['start_url']}")
            try:
                rows, trajectory = collect_task(
                    task=task,
                    page=page,
                    output_dir=args.output_dir,
                    metric_computer=metric_computer,
                    timeout_ms=args.timeout_ms,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  task failed: {exc}")
                try:
                    page.close()
                except Exception:
                    pass
                page = context.new_page()
                continue

            all_rows.extend(rows)
            with audit_path.open("a", encoding="utf-8", newline="\n") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            write_jsonl(replay_dir / f"{task['task_id']}.jsonl", [trajectory])
            print(f"  rows={len(rows)} labels={dict(Counter(row['failure_type_4'] for row in rows))}")
        context.close()
        browser.close()

    print(json.dumps({
        "tasks": len(tasks),
        "rows": len(all_rows),
        "outcome": dict(Counter(row["outcome_label"] for row in all_rows)),
        "failure_type_4": dict(Counter(row["failure_type_4"] for row in all_rows)),
        "audit_file": str(audit_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
