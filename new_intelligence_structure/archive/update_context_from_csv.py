import csv
import json
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "archive" / "Intelligence-Domain-Map.csv"
DATASET_DIR = BASE_DIR / "dataset"


def load_context_rows():
    rows = defaultdict(list)
    with CSV_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            key = (row["Domain Name"].strip(), row["Intelligence Name"].strip())
            rows[key].append(row)
    return rows


def select_row(rows, metadata, path):
    key = (str(metadata.get("domain", "")).strip(), str(metadata.get("name", "")).strip())
    candidates = rows.get(key, [])
    if not candidates:
        raise ValueError(f"No CSV match for {key} in {path}")
    if len(candidates) == 1:
        return candidates[0]

    description = str(metadata.get("description", "")).strip()
    description_matches = [
        row for row in candidates
        if row["Intelligence Description"].strip() == description
    ]
    if len(description_matches) != 1:
        raise ValueError(f"Ambiguous CSV match for {key} in {path}")
    return description_matches[0]


def main():
    rows = load_context_rows()
    updated = 0
    unchanged = 0

    for path in sorted(DATASET_DIR.rglob("*.json")):
        with path.open("r", encoding="utf-8") as json_file:
            data = json.load(json_file)

        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"Missing metadata object in {path}")

        row = select_row(rows, metadata, path)
        context = row["Context"].strip()
        if metadata.get("context") == context:
            unchanged += 1
            continue

        metadata["context"] = context
        with path.open("w", encoding="utf-8", newline="\n") as json_file:
            json.dump(data, json_file, indent=2, ensure_ascii=False)
            json_file.write("\n")
        updated += 1

    print(f"Updated: {updated}")
    print(f"Unchanged: {unchanged}")
    print(f"Processed: {updated + unchanged}")


if __name__ == "__main__":
    main()