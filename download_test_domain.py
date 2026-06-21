"""
Download the test_domain split from osunlp/Multimodal-Mind2Web dataset.

Dataset: https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web
Split: test_domain — 4060 actions from 694 tasks (entire domains not seen during training)

Usage:
    python download_test_domain.py
    python download_test_domain.py --output_dir dataset/test_domain_data
    python download_test_domain.py --save_format jsonl
    python download_test_domain.py --save_screenshots
"""

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download test_domain split from Multimodal-Mind2Web"
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test_domain",
        help="Dataset split to download (default: test_domain). Options: train, test_domain, test_task, test_website",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Directory to save the downloaded data (default: dataset/<split>)",
    )
    parser.add_argument(
        "--cache_dir",
        type=str,
        default=None,
        help="HuggingFace cache directory (default: ~/.cache/huggingface)",
    )
    parser.add_argument(
        "--save_format",
        type=str,
        choices=["json", "jsonl", "parquet", "arrow"],
        default="jsonl",
        help="Format to save the data (default: jsonl)",
    )
    parser.add_argument(
        "--save_screenshots",
        action="store_true",
        help="Save screenshot images as separate files in a screenshots/ subfolder",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of rows to download (for testing). Downloads all by default.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Check dependencies ──────────────────────────────────────────────
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ 'datasets' library not found. Install it with:")
        print("   pip install datasets")
        sys.exit(1)

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        if args.save_screenshots:
            print("❌ 'Pillow' library not found (needed for --save_screenshots). Install it with:")
            print("   pip install Pillow")
            sys.exit(1)

    # ── Create output directory ─────────────────────────────────────────
    split_name = args.split
    output_dir = Path(args.output_dir) if args.output_dir else Path(f"dataset/{split_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir.resolve()}")

    # ── Download the split ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Downloading '{split_name}' split from Multimodal-Mind2Web...")
    print("   Dataset: osunlp/Multimodal-Mind2Web")
    print(f"   Split:   {split_name}")
    print("=" * 60 + "\n")

    dataset = load_dataset(
        "osunlp/Multimodal-Mind2Web",
        split=split_name,
        cache_dir=args.cache_dir,
    )

    if args.limit:
        dataset = dataset.select(range(min(args.limit, len(dataset))))
        print(f"⚠️  Limited to {len(dataset)} rows (--limit {args.limit})")

    print(f"✅ Downloaded {len(dataset):,} rows")
    print(f"   Columns: {dataset.column_names}")

    # ── Save screenshots separately (optional) ─────────────────────────
    if args.save_screenshots and "screenshot" in dataset.column_names:
        screenshots_dir = output_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        print(f"\n🖼️  Saving screenshots to {screenshots_dir}/...")

        saved_count = 0
        skipped_count = 0
        for i, row in enumerate(dataset):
            img = row.get("screenshot")
            if img is not None:
                # The screenshot field is a PIL Image when loaded by datasets
                action_uid = row.get("action_uid", f"action_{i:05d}")
                img_path = screenshots_dir / f"{action_uid}.png"
                if img_path.exists():
                    skipped_count += 1
                else:
                    try:
                        img.save(str(img_path))
                        saved_count += 1
                    except Exception as e:
                        print(f"   ⚠️  Failed to save screenshot {i}: {e}")

            if (i + 1) % 500 == 0:
                print(f"   Progress: {i + 1:,}/{len(dataset):,} (saved: {saved_count}, skipped: {skipped_count})")

        print(f"   Newly saved: {saved_count}, Skipped (existing): {skipped_count}")

        print(f"   ✅ Screenshots saved: {len(list(screenshots_dir.glob('*.png'))):,} files")

    # ── Save dataset ────────────────────────────────────────────────────
    print(f"\n💾 Saving data in {args.save_format} format...")

    # Remove image column for text-based formats (images can't serialize to JSON)
    text_formats = {"json", "jsonl"}
    save_dataset = dataset

    if args.save_format in text_formats and "screenshot" in dataset.column_names:
        print("   ℹ️  Removing screenshot column for text format (use --save_screenshots to save images separately)")
        save_dataset = dataset.remove_columns(["screenshot"])

    if args.save_format == "jsonl":
        output_file = output_dir / f"{split_name}.jsonl"
        save_dataset.to_json(str(output_file), lines=True)
        print(f"   ✅ Saved to {output_file}")

    elif args.save_format == "json":
        output_file = output_dir / f"{split_name}.json"
        save_dataset.to_json(str(output_file), lines=False)
        print(f"   ✅ Saved to {output_file}")

    elif args.save_format == "parquet":
        output_file = output_dir / f"{split_name}.parquet"
        save_dataset.to_parquet(str(output_file))
        print(f"   ✅ Saved to {output_file}")

    elif args.save_format == "arrow":
        output_file = output_dir / "test_domain.arrow"
        save_dataset.save_to_disk(str(output_dir / "test_domain_arrow"))
        print(f"   ✅ Saved to {output_dir / 'test_domain_arrow'}")

    # ── Print summary ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📊 DATASET SUMMARY")
    print("=" * 60)
    print(f"   Total rows:     {len(dataset):,}")

    # Count unique tasks and domains
    if "annotation_id" in dataset.column_names:
        unique_tasks = len(set(dataset["annotation_id"]))
        print(f"   Unique tasks:   {unique_tasks:,}")
    if "domain" in dataset.column_names:
        unique_domains = len(set(dataset["domain"]))
        print(f"   Unique domains: {unique_domains:,}")
    if "website" in dataset.column_names:
        unique_websites = len(set(dataset["website"]))
        print(f"   Unique websites: {unique_websites:,}")

    # Show sample
    print("\n📝 Sample row (first entry):")
    sample = dataset[0]
    for key, value in sample.items():
        if key == "screenshot":
            print(f"   {key}: <PIL.Image>")
        elif key in ("raw_html", "cleaned_html"):
            val_str = str(value)
            print(f"   {key}: ({len(val_str):,} chars)")
        elif isinstance(value, str) and len(value) > 100:
            print(f"   {key}: {value[:100]}...")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
