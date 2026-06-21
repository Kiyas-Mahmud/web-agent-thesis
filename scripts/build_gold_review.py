"""Build a JSONL and HTML review queue from gold_audit.jsonl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gold_collection.gold_review import write_review_html, write_review_queue  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build gold dataset review artifacts.")
    parser.add_argument("--audit-file", default="output/gold_dataset/gold_audit.jsonl")
    parser.add_argument("--output-dir", default="output/gold_dataset/review")
    parser.add_argument("--limit", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    queue = write_review_queue(args.audit_file, output_dir / "review_queue.jsonl", limit=args.limit)
    page = write_review_html(
        args.audit_file,
        output_dir / "review.html",
        image_base="..",
        limit=min(args.limit, 200),
    )
    print(f"Review queue: {queue}")
    print(f"Review HTML: {page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
