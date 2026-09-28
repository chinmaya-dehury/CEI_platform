import json
import csv
import os
from pathlib import Path

# Base directory containing the intelligence JSON files (the new_intelligence_structure folder)
BASE_DIR = Path(__file__).resolve().parent

# Output CSV path (will be created in the same folder)
OUTPUT_CSV = BASE_DIR / "intelligence_summary.csv"

header = ["Domain Name", "Intelligence Name", "Intelligence Description"]
rows = []

# Walk through all JSON files recursively
for json_file in BASE_DIR.rglob("*.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        domain = meta.get("domain", "")
        name = meta.get("name", "")
        description = meta.get("description", "")
        rows.append([domain, name, description])
    except Exception as e:
        # Skip files that cannot be read or do not have expected structure
        print(f"Skipping {json_file}: {e}")

# Write rows to CSV
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)
    writer.writerows(rows)

print(f"Extracted {len(rows)} records to {OUTPUT_CSV}")
