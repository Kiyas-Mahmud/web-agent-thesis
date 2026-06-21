"""Inspect raw Mind2Web row format to fix the parser."""
import sys
sys.path.insert(0, 'src')

from datasets import load_dataset
import json

print("Streaming 1 row from Mind2Web...")
ds = load_dataset("osunlp/Multimodal-Mind2Web", split="train", streaming=True)

for i, row in enumerate(ds):
    print("\n=== ROW FIELDS ===")
    for k, v in row.items():
        if k == "pos_candidates":
            print(f"  pos_candidates type: {type(v).__name__}  len={len(v)}")
            if v:
                print(f"    [0] type: {type(v[0]).__name__}")
                print(f"    [0] value: {repr(v[0])[:300]}")
                if len(v) > 1:
                    print(f"    [1] type: {type(v[1]).__name__}")
                    print(f"    [1] value: {repr(v[1])[:200]}")
        elif k == "operation":
            print(f"  operation type: {type(v).__name__}  value: {repr(v)[:200]}")
        elif k == "screenshot" or k == "image":
            print(f"  {k}: <binary, len={len(v) if v else 0}>")
        else:
            print(f"  {k}: {repr(v)[:120]}")
    if i >= 0:   # just one row
        break

print("\nDONE")
