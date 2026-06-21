"""Format JSONL files with proper JSON structure"""
import json
from pathlib import Path

# Format mind2web.jsonl (full trajectories)
print("Formatting mind2web.jsonl...")
input_file = Path('dataset/collected/mind2web.jsonl')
output_file = Path('dataset/collected/mind2web_formatted.json')

if input_file.exists():
    trajectories = []
    for line in input_file.read_text(encoding='utf-8').splitlines():
        if line.strip():
            trajectories.append(json.loads(line))
    
    # Write as properly formatted JSON array
    output_file.write_text(
        json.dumps(trajectories, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"  ✅ Created: {output_file}")
    print(f"  📊 {len(trajectories)} trajectories formatted")
else:
    print(f"  ⚠️  File not found: {input_file}")

print()

# Format mind2web_training.jsonl (training steps)
print("Formatting mind2web_training.jsonl...")
input_file = Path('dataset/collected/mind2web_training.jsonl')
output_file = Path('dataset/collected/mind2web_training_formatted.json')

if input_file.exists():
    steps = []
    for line in input_file.read_text(encoding='utf-8').splitlines():
        if line.strip():
            steps.append(json.loads(line))
    
    # Write as properly formatted JSON array
    output_file.write_text(
        json.dumps(steps, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"  ✅ Created: {output_file}")
    print(f"  📊 {len(steps)} steps formatted")
else:
    print(f"  ⚠️  File not found: {input_file}")

print()
print("=" * 70)
print("✅ FORMATTING COMPLETE!")
print()
print("Original JSONL files (1 line per record):")
print("  • dataset/collected/mind2web.jsonl")
print("  • dataset/collected/mind2web_training.jsonl")
print()
print("Formatted JSON files (pretty-printed):")
print("  • dataset/collected/mind2web_formatted.json")
print("  • dataset/collected/mind2web_training_formatted.json")
print()
print("💡 TIP: Open *_formatted.json files in VS Code for readable structure")
print("=" * 70)
