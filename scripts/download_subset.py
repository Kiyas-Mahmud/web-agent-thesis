"""
Download a subset of Multimodal Mind2Web dataset.
Following recommended approach to avoid large downloads.

Usage:
    python scripts/download_subset.py --num-samples 100
    python scripts/download_subset.py --percentage 5
"""

import argparse
import logging
import sys
from pathlib import Path
from datasets import load_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Download subset of Multimodal Mind2Web")
    parser.add_argument(
        "--num-samples",
        type=int,
        default=None,
        help="Number of samples to download (e.g., 100, 500, 1000)"
    )
    parser.add_argument(
        "--percentage",
        type=int,
        default=None,
        help="Percentage of dataset to download (e.g., 5, 10)"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="dataset/mind2web_subset",
        help="Directory to cache downloaded subset"
    )
    parser.add_argument(
        "--use-auth",
        action="store_true",
        help="Use HuggingFace authentication token"
    )
    
    args = parser.parse_args()
    
    # Determine split specification
    if args.num_samples:
        split_spec = f"train[:{args.num_samples}]"
        logger.info(f"Downloading first {args.num_samples} samples from train split")
    elif args.percentage:
        split_spec = f"train[:{args.percentage}%]"
        logger.info(f"Downloading first {args.percentage}% of train split")
    else:
        # Default: 100 samples
        split_spec = "train[:100]"
        logger.info("Downloading first 100 samples from train split (default)")
    
    logger.info("="*60)
    logger.info("Multimodal Mind2Web Subset Downloader")
    logger.info("="*60)
    logger.info(f"Dataset: osunlp/Multimodal-Mind2Web")
    logger.info(f"Split: {split_spec}")
    logger.info(f"Cache dir: {args.cache_dir}")
    logger.info("="*60)
    
    try:
        # Create cache directory
        Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Download subset
        logger.info("\n📥 Starting download...")
        logger.info("(This will only download the specified subset, not full 8.4GB)")
        
        dataset = load_dataset(
            "osunlp/Multimodal-Mind2Web",
            split=split_spec,
            cache_dir=args.cache_dir,
            trust_remote_code=True if args.use_auth else None
        )
        
        logger.info(f"\n✅ Download completed successfully!")
        logger.info(f"   Total samples: {len(dataset)}")
        logger.info(f"   Features: {list(dataset.features.keys())}")
        
        # Show sample info
        if len(dataset) > 0:
            sample = dataset[0]
            logger.info(f"\n📊 Sample data structure:")
            for key in sample.keys():
                value = sample[key]
                if isinstance(value, bytes):
                    logger.info(f"   {key}: <bytes data>")
                elif isinstance(value, dict):
                    logger.info(f"   {key}: <dict with {len(value)} keys>")
                elif isinstance(value, list):
                    logger.info(f"   {key}: <list with {len(value)} items>")
                else:
                    value_str = str(value)[:50]
                    logger.info(f"   {key}: {value_str}...")
        
        # Validate data
        logger.info(f"\n🔍 Validating subset...")
        tasks_with_images = 0
        total_steps = 0
        
        for idx in range(min(5, len(dataset))):
            sample = dataset[idx]
            if 'screenshot' in sample or 'screenshots' in sample:
                tasks_with_images += 1
            if 'actions' in sample:
                if isinstance(sample['actions'], list):
                    total_steps += len(sample['actions'])
        
        logger.info(f"   Checked {min(5, len(dataset))} samples")
        logger.info(f"   Tasks with images: {tasks_with_images}")
        logger.info(f"   Total steps in sample: {total_steps}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Subset download completed successfully!")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Download failed: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Check internet connection")
        logger.error("2. Try with authentication: --use-auth")
        logger.error("3. Try smaller subset: --num-samples 50")
        logger.error("4. Check HuggingFace status: https://status.huggingface.co")
        return 1


if __name__ == "__main__":
    sys.exit(main())
