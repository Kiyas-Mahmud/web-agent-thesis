"""Quick test: verify the loader can see test splits."""
from src.offline_data.mind2web_loader import MultimodalMind2WebLoader

loader = MultimodalMind2WebLoader(cache_dir="dataset/mind2web_offline")
success = loader.load_from_cache(splits_to_load=['test_domain', 'test_task', 'test_website'])

if success:
    info = loader.get_dataset_info()
    for split_name, data in info["splits"].items():
        print(f"  {split_name}: {data['num_samples']} samples")
    print("\nLoader is ready!")
else:
    print("FAILED to load from cache")
