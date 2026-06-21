"""
Load partial dataset directly from cached parquet files.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("Loading Partial Cached Dataset")
print("=" * 60)

# Read parquet files directly
import os
import pandas as pd
from datasets import Dataset

cache_path = Path(os.path.expanduser("~/.cache/huggingface/hub/datasets--osunlp--Multimodal-Mind2Web"))
print(f"\n📂 Cache Directory: {cache_path}")

# Find all parquet files
parquet_files = sorted(cache_path.rglob("train-*.parquet"))
print(f"✅ Found {len(parquet_files)} cached parquet files")

# Load first file as test
print(f"\n📊 Testing first file: {parquet_files[0].name}")
try:
    df = pd.read_parquet(parquet_files[0])
    print(f"   ✅ Loaded successfully")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {list(df.columns)[:5]}...")
    
    # Convert to HF dataset
    dataset = Dataset.from_pandas(df)
    print(f"\n   Dataset info:")
    print(f"   - Num rows: {len(dataset)}")
    print(f"   - Features: {list(dataset.features.keys())[:10]}...")
    
    # Show sample
    print(f"\n   Sample data:")
    sample = dataset[0]
    print(f"   - annotation_id: {sample.get('annotation_id', 'N/A')}")
    print(f"   - website: {sample.get('website', 'N/A')}")
    print(f"   - domain: {sample.get('domain', 'N/A')}")
    print(f"   - action_uid: {sample.get('action_uid', 'N/A')}")
    
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
