"""
Download and validate Multimodal Mind2Web dataset.

Usage:
    python scripts/download_mind2web.py --validate --num-samples 20
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.offline_data import MultimodalMind2WebLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Download Multimodal Mind2Web dataset")
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="dataset/mind2web_offline",
        help="Directory to cache downloaded dataset"
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force re-download even if cached"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate dataset after download"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=10,
        help="Number of samples to validate"
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        choices=["train", "test_task", "test_website", "test_domain"],
        help="Dataset split to validate"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("Multimodal Mind2Web Dataset Downloader")
    logger.info("="*60)
    
    # Initialize loader
    loader = MultimodalMind2WebLoader(cache_dir=args.cache_dir)
    
    # Download dataset
    logger.info("\n📥 Downloading dataset from HuggingFace...")
    success = loader.download_dataset(force_download=args.force_download)
    
    if not success:
        logger.error("❌ Download failed")
        return 1
    
    # Get dataset info
    logger.info("\n📊 Dataset Information:")
    info = loader.get_dataset_info()
    for key, value in info.items():
        if key == "splits":
            logger.info(f"\n  Splits:")
            for split_name, split_info in value.items():
                logger.info(f"    {split_name}:")
                logger.info(f"      Samples: {split_info['num_samples']}")
                logger.info(f"      Features: {', '.join(split_info['features'][:5])}...")
        else:
            logger.info(f"  {key}: {value}")
    
    # Validate if requested
    if args.validate:
        logger.info(f"\n🔍 Validating {args.num_samples} samples from '{args.split}' split...")
        validation_report = loader.validate_dataset(
            split=args.split,
            num_samples=args.num_samples
        )
        
        logger.info("\n📋 Validation Report:")
        logger.info(f"  Trajectories loaded: {validation_report['total_trajectories']}")
        logger.info(f"  Total steps: {validation_report['total_steps']}")
        logger.info(f"  Valid steps: {validation_report['valid_steps']} ({validation_report.get('valid_step_percentage', 0):.1f}%)")
        logger.info(f"  Invalid steps: {validation_report['invalid_steps']}")
        logger.info(f"  Screenshot coverage: {validation_report.get('screenshot_coverage', 0):.1f}%")
        logger.info(f"  Bbox coverage: {validation_report.get('bbox_coverage', 0):.1f}%")
        
        if validation_report['validation_errors']:
            logger.info(f"\n  Common validation errors:")
            error_counts = {}
            for error in validation_report['validation_errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
            for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:5]:
                logger.info(f"    - {error}: {count} occurrences")
    
    logger.info("\n✅ Dataset download complete!")
    logger.info(f"Cache location: {args.cache_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
