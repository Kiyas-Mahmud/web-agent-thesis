"""
Quick diagnostic to check if downloaded data is accessible.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("Data Availability Check")
print("=" * 60)

# Check cache directory
import os
cache_path = Path(os.path.expanduser("~/.cache/huggingface/hub/datasets--osunlp--Multimodal-Mind2Web"))
print(f"\n1. Cache Directory: {cache_path}")
print(f"   Exists: {cache_path.exists()}")

if cache_path.exists():
    # List parquet files
    parquet_files = list(cache_path.rglob("*.parquet"))
    print(f"   Parquet files found: {len(parquet_files)}")
    
    if parquet_files:
        print(f"\n   Sample files:")
        for f in sorted(parquet_files)[:5]:
            size_mb = f.stat().st_size / (1024*1024)
            print(f"      {f.name} ({size_mb:.1f} MB)")

# Try loading with datasets library
print("\n2. Testing datasets library load...")
try:
    from datasets import load_dataset
    
    # Try loading from cache
    print("   Attempting to load from HuggingFace cache...")
    dataset = load_dataset("osunlp/Multimodal-Mind2Web")
    
    print(f"   ✅ SUCCESS!")
    print(f"   Available splits: {list(dataset.keys())}")
    for split_name, split_data in dataset.items():
        print(f"      {split_name}: {len(split_data)} samples")
    
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print(f"\n   Error type: {type(e).__name__}")

print("\n" + "=" * 60)
