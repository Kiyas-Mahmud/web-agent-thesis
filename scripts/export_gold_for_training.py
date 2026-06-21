"""Export leakage-safe train/val/test files from gold_audit.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gold_collection import GoldExportConfig, GoldExporter  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export gold dataset for model training.")
    parser.add_argument("--audit-file", default="output/gold_dataset/gold_audit.jsonl")
    parser.add_argument("--output-dir", default="output/gold_dataset")
    parser.add_argument("--approved-only", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = GoldExporter(
        GoldExportConfig(
            input_audit=args.audit_file,
            output_dir=args.output_dir,
            approved_only=args.approved_only,
            seed=args.seed,
        )
    ).export()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
