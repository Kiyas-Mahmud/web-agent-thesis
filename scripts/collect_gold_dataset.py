"""Collect the main gold dataset from an ActionLog JSON/JSONL file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from browser_replay import LogParser  # noqa: E402
from gold_collection import GoldCollectionConfig, GoldCollector  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect leakage-safe gold data.")
    parser.add_argument("--log-file", type=Path, required=True, help="JSON/JSONL ActionLog file.")
    parser.add_argument("--output-dir", default="output/gold_dataset")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--step-delay-ms", type=int, default=500)
    parser.add_argument("--max-steps", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_logs = LogParser().load_file(args.log_file)
    logs = all_logs[args.offset : args.offset + args.limit]
    print(f"Loaded {len(all_logs)} tasks; collecting offset={args.offset}, count={len(logs)}")
    collector = GoldCollector(
        GoldCollectionConfig(
            output_dir=args.output_dir,
            headless=not args.no_headless,
            timeout_ms=args.timeout_ms,
            step_delay_ms=args.step_delay_ms,
            max_steps=args.max_steps,
        )
    )
    steps = collector.collect_logs(logs)
    print(f"Collected gold steps: {len(steps)} from {len(logs)} tasks")
    print(f"Audit file: {collector.audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
