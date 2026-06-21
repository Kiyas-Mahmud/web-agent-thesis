"""
Simple direct download of Mind2Web dataset (smaller sample for testing).

Uses datasets library streaming mode to avoid large downloads.
"""

import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("Simple Mind2Web Dataset Test")
    logger.info("="*60)
    
    try:
        from datasets import load_dataset
        
        logger.info("\nAttempting to load dataset in streaming mode...")
        logger.info("This will download minimal data for testing.")
        
        # Try streaming mode first (no full download)
        dataset = load_dataset(
            "osunlp/Multimodal-Mind2Web",
            streaming=True,
            split="train"
        )
        
        logger.info("✅ Dataset loaded in streaming mode")
        
        # Try to get first few samples
        logger.info("\nFetching first 5 samples...")
        samples = []
        for i, sample in enumerate(dataset):
            if i >= 5:
                break
            samples.append(sample)
            logger.info(f"  Sample {i+1}: {sample.get('annotation_id', 'unknown')}")
        
        logger.info(f"\n✅ Successfully loaded {len(samples)} samples")
        logger.info("\nDataset structure:")
        if samples:
            logger.info(f"  Keys: {list(samples[0].keys())}")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check internet connection")
        logger.info("2. Try: pip install --upgrade datasets huggingface-hub")
        logger.info("3. Check HuggingFace status: https://status.huggingface.co")
        return 1


if __name__ == "__main__":
    sys.exit(main())
