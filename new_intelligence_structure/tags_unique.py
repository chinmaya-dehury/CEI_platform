import glob
import json
import os

BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure\dataset'

all_tags = []

# Find all JSON files
json_files = glob.glob(os.path.join(BASE_DIR, '**', '*.json'), recursive=True)

for fp in json_files:
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tags = data.get('metadata', {}).get('tags', [])
            # Convert tags to lowercase to prevent case-sensitivity duplicates
            all_tags.extend([str(t).lower().strip() for t in tags])
    except Exception:
        pass

print(f"Total tags across dataset: {len(all_tags)}")
print(f"Unique tags across dataset: {len(set(all_tags))}")
print(f"Unique tags: {set(all_tags)}")