"""Generate the local v4 balanced gold collection seed.

This seed is a scale-up pilot, not the final thesis dataset. It keeps repeated
task/action text balanced across success and failure while adding controlled
observed `ACTION_MISMATCH` and `LOOP_DETECTED` examples.
"""

from __future__ import annotations

import argparse
import json
from itertools import cycle
from pathlib import Path
from random import Random
from typing import Any


QUERY_VALUES = [
    "web automation",
    "browser testing",
    "machine learning",
    "data science",
    "accessibility",
    "python asyncio",
    "transformer models",
    "array indexing",
]


SUCCESS_TEMPLATES: list[dict[str, Any]] = [
    {"domain": "wikipedia.org", "url": "https://www.wikipedia.org", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#searchInput"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#id-search-field"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#search"},
    {"domain": "arxiv.org", "url": "https://arxiv.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "form.mini-search input[name=\"query\"]"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/doc/\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"https://docs.pypi.org/\"]"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"https://numpy.org/doc/stable\"]"},
    {"domain": "pandas.pydata.org", "url": "https://pandas.pydata.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"docs/\"]"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "downloads", "task": "Click the Downloads link.", "action": "CLICK", "target": "a[href=\"/downloads/\"]"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "install", "task": "Click the Install link.", "action": "CLICK", "target": "a[href=\"/install\"]"},
    {"domain": "scikit-learn.org", "url": "https://scikit-learn.org/stable/", "intent": "install", "task": "Click the Install link.", "action": "CLICK", "target": "a[href=\"install.html\"]"},
    {"domain": "scikit-learn.org", "url": "https://scikit-learn.org/stable/", "intent": "api", "task": "Click the API link.", "action": "CLICK", "target": "a[href=\"api/index.html\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "help", "task": "Click the Help link.", "action": "CLICK", "target": "a[href=\"/help/\"]"},
    {"domain": "arxiv.org", "url": "https://arxiv.org/", "intent": "help", "task": "Click the Help link.", "action": "CLICK", "target": "a[href=\"https://info.arxiv.org/help\"]"},
    {"domain": "w3.org", "url": "https://www.w3.org/", "intent": "about", "task": "Click the About link.", "action": "CLICK", "target": "a[href=\"/about/\"]:visible"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "about", "task": "Click the About link.", "action": "CLICK", "target": "a[href=\"/about\"]"},
]


PERCEPTION_TEMPLATES: list[dict[str, Any]] = [
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "input[name=\"q\"]"},
    {"domain": "pandas.pydata.org", "url": "https://pandas.pydata.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "input[name=\"q\"]"},
    {"domain": "w3.org", "url": "https://www.w3.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "input[name=\"q\"]"},
    {"domain": "wikipedia.org", "url": "https://www.wikipedia.org", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/docs/\"]"},
    {"domain": "w3.org", "url": "https://www.w3.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/docs/\"]"},
    {"domain": "arxiv.org", "url": "https://arxiv.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/docs\"]"},
    {"domain": "wikipedia.org", "url": "https://www.wikipedia.org", "intent": "downloads", "task": "Click the Downloads link.", "action": "CLICK", "target": "a[href=\"/downloads/\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "downloads", "task": "Click the Downloads link.", "action": "CLICK", "target": "a[href=\"/downloads/\"]"},
    {"domain": "wikipedia.org", "url": "https://www.wikipedia.org", "intent": "install", "task": "Click the Install link.", "action": "CLICK", "target": "a[href=\"/install\"]"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "api", "task": "Click the API link.", "action": "CLICK", "target": "a[href=\"/api/\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "api", "task": "Click the API link.", "action": "CLICK", "target": "a[href=\"/api/\"]"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "help", "task": "Click the Help link.", "action": "CLICK", "target": "a[href=\"/help\"]"},
    {"domain": "pandas.pydata.org", "url": "https://pandas.pydata.org/", "intent": "help", "task": "Click the Help link.", "action": "CLICK", "target": "a[href=\"help.html\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "about", "task": "Click the About link.", "action": "CLICK", "target": "a[href=\"/about/\"]"},
    {"domain": "arxiv.org", "url": "https://arxiv.org/", "intent": "about", "task": "Click the About link.", "action": "CLICK", "target": "a[href=\"/about\"]"},
]


ACTION_MISMATCH_TEMPLATES: list[dict[str, Any]] = [
    {"domain": "python.org", "url": "https://www.python.org", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/downloads/\"]"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "downloads", "task": "Click the Downloads link.", "action": "CLICK", "target": "a[href=\"/doc/\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/help/\"]"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "help", "task": "Click the Help link.", "action": "CLICK", "target": "a[href=\"https://docs.pypi.org/\"]"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "documentation", "task": "Click the Documentation link.", "action": "CLICK", "target": "a[href=\"/install\"]"},
    {"domain": "numpy.org", "url": "https://numpy.org/", "intent": "install", "task": "Click the Install link.", "action": "CLICK", "target": "a[href=\"https://numpy.org/doc/stable\"]"},
    {"domain": "scikit-learn.org", "url": "https://scikit-learn.org/stable/", "intent": "install", "task": "Click the Install link.", "action": "CLICK", "target": "a[href=\"api/index.html\"]"},
    {"domain": "scikit-learn.org", "url": "https://scikit-learn.org/stable/", "intent": "api", "task": "Click the API link.", "action": "CLICK", "target": "a[href=\"install.html\"]"},
]


LOOP_TEMPLATES: list[dict[str, Any]] = [
    {"domain": "wikipedia.org", "url": "https://www.wikipedia.org", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#searchInput"},
    {"domain": "python.org", "url": "https://www.python.org", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#id-search-field"},
    {"domain": "pypi.org", "url": "https://pypi.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "#search"},
    {"domain": "arxiv.org", "url": "https://arxiv.org/", "intent": "site_search", "task": "Type a query into the site search field.", "action": "TYPE", "target": "form.mini-search input[name=\"query\"]"},
]


def action_from_template(template: dict[str, Any], value: str) -> dict[str, Any]:
    action = {
        "action_type": template["action"],
        "target": template["target"],
        "timeout": 5000 if template["action"] == "CLICK" else 5000,
        "description": template["task"].rstrip("."),
    }
    if template["action"] == "TYPE":
        action["value"] = value
    return action


def build_task(task_id: str, template: dict[str, Any], behavior: str, value: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "start_url": template["url"],
        "task_description": template["task"],
        "source": "custom",
        "metadata": {
            "domain": template["domain"],
            "collection_type": "gold_final_v4_local_300",
            "expected_behavior": behavior,
            "intent": template["intent"],
        },
        "actions": [action_from_template(template, value)],
    }


def build_loop_task(task_id: str, template: dict[str, Any], value: str) -> dict[str, Any]:
    action = action_from_template(template, value)
    return {
        "task_id": task_id,
        "start_url": template["url"],
        "task_description": template["task"],
        "source": "custom",
        "metadata": {
            "domain": template["domain"],
            "collection_type": "gold_final_v4_local_300",
            "expected_behavior": "mixed",
            "expected_step_behaviors": ["success", "loop_detected"],
            "intent": template["intent"],
        },
        "actions": [dict(action), dict(action)],
    }


def generate_tasks() -> list[dict[str, Any]]:
    tasks = []
    next_id = 1
    values = cycle(QUERY_VALUES)

    success_cycle = cycle(SUCCESS_TEMPLATES)
    for _ in range(128):
        template = next(success_cycle)
        tasks.append(build_task(f"gold_v4_{next_id:06d}", template, "success", next(values)))
        next_id += 1

    perception_cycle = cycle(PERCEPTION_TEMPLATES)
    for _ in range(64):
        tasks.append(
            build_task(
                f"gold_v4_{next_id:06d}",
                next(perception_cycle),
                "perception_error",
                next(values),
            )
        )
        next_id += 1

    mismatch_cycle = cycle(ACTION_MISMATCH_TEMPLATES)
    for _ in range(64):
        tasks.append(
            build_task(
                f"gold_v4_{next_id:06d}",
                next(mismatch_cycle),
                "action_mismatch",
                next(values),
            )
        )
        next_id += 1

    loop_cycle = cycle(LOOP_TEMPLATES)
    for _ in range(64):
        tasks.append(build_loop_task(f"gold_v4_{next_id:06d}", next(loop_cycle), next(values)))
        next_id += 1

    Random(42).shuffle(tasks)
    return tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate v4 local gold seed.")
    parser.add_argument("--output", type=Path, default=Path("config/gold_tasks_final_v4_local_300.jsonl"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = generate_tasks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    steps = sum(len(task["actions"]) for task in tasks)
    print(f"Wrote {len(tasks)} tasks / {steps} steps to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
