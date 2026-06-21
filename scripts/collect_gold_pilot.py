"""Collect a small gold-dataset pilot run.

Examples:
    python scripts/collect_gold_pilot.py --log-file logs/gold_tasks.jsonl --limit 50
    python scripts/collect_gold_pilot.py --limit 3 --no-headless
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from browser_replay import ActionLog, LogAction  # noqa: E402
from gold_collection import GoldCollectionConfig, GoldCollector  # noqa: E402


def built_in_smoke_logs(limit: int) -> list[ActionLog]:
    logs = [
        ActionLog(
            task_id=f"gold_smoke_{idx:03d}",
            start_url="https://example.com",
            task_description="Open a stable public page and wait for the visible content.",
            source="custom",
            metadata={"domain": "example.com", "pilot": True},
            actions=[
                LogAction(action_type="WAIT", timeout=1000, description="Wait for page stability"),
            ],
        )
        for idx in range(max(1, limit))
    ]
    return logs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect a gold pilot dataset.")
    parser.add_argument("--log-file", type=Path, default=None, help="JSON/JSONL ActionLog file.")
    parser.add_argument("--output-dir", default="output/gold_dataset")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--step-delay-ms", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collector = GoldCollector(
        GoldCollectionConfig(
            output_dir=args.output_dir,
            headless=not args.no_headless,
            timeout_ms=args.timeout_ms,
            step_delay_ms=args.step_delay_ms,
        )
    )

    if args.log_file:
        steps = collector.collect_file(args.log_file)
    else:
        steps = collector.collect_logs(built_in_smoke_logs(args.limit))

    print(f"Collected pilot gold steps: {len(steps)}")
    print(f"Audit file: {collector.audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
