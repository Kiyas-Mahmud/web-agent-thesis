"""Show all unique websites and sample records from Mind2Web dataset."""
from datasets import load_dataset
from collections import Counter

all_websites = []
examples = []

for split in ['train', 'test_domain', 'test_task', 'test_website']:
    ds = load_dataset('osunlp/Multimodal-Mind2Web', split=split, cache_dir='dataset/mind2web_offline')
    websites = ds['website']
    all_websites.extend(websites)
    # Pick 3 examples from this split
    indices = [0, len(ds)//3, 2*len(ds)//3]
    for idx in indices:
        examples.append({
            'split': split,
            'annotation_id': ds[idx]['annotation_id'],
            'website': ds[idx]['website'],
            'confirmed_task': ds[idx]['confirmed_task']
        })

counts = Counter(all_websites)

print('='*70)
print('ALL UNIQUE WEBSITES IN MIND2WEB DATASET')
print('='*70)
print(f'Total unique websites: {len(counts)}')
print(f'Total samples across all splits: {len(all_websites)}')
print()

for website, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
    print(f'  {website}: {count} samples')

print()
print('='*70)
print('SAMPLE RECORDS FROM EACH SPLIT')
print('='*70)
for ex in examples:
    print(f"\nSplit: {ex['split']}")
    print(f"  annotation_id:  {ex['annotation_id']}")
    print(f"  website:        {ex['website']}")
    print(f"  confirmed_task: {ex['confirmed_task']}")
