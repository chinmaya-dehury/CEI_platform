import csv
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "dataset"
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_DIR = RESULTS_DIR / "cluster_insights"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(override=True)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

# Set to "overlap" to analyze every cluster membership above the threshold.
ASSIGNMENT_MODE = "dominant"
OVERLAP_THRESHOLD = 0.40
MAX_RETRIES = 2

MEMBERSHIP_FILES = {
    "baseline_cosine": RESULTS_DIR / "result_cosine_baseline_corrected" / "fuzzy_membership_matrix.csv",
    "pcm_cosine": RESULTS_DIR / "result_cosine_pcm" / "fuzzy_membership_matrix.csv",
    "baseline_llm": RESULTS_DIR / "result_llm_baseline" / "fuzzy_membership_matrix.csv",
    "pcm_llm": RESULTS_DIR / "result_llm_pcm" / "fuzzy_membership_K8.csv",
}

ANALYSIS_PROMPT = """You are a cluster-insight analyst.

You will receive the items belonging to ONE cluster.

Analyze the cluster and determine whether it contains a clear, meaningful, and coherent pattern.

Tasks:
1. Identify the main common theme, behavior, capability, or characteristic shared by the items.
2. Explain the key insight represented by this cluster in 1-3 sentences.
3. Identify the strongest evidence from the items supporting the insight.
4. Check whether the items are sufficiently coherent or whether they appear unrelated.
5. Decide whether the cluster is meaningful based on its internal pattern.

Return ONLY this JSON object:
{
  "valid": true,
  "insight": "short description of the discovered pattern",
  "evidence": ["key evidence 1", "key evidence 2"],
  "coherence": 0.0,
  "reason": "short explanation"
}

Important:
- Do not invent information that is not present in the items.
- Do not judge the cluster based only on similarity.
- A cluster is valid if you can identify a clear, non-trivial, interpretable pattern from its members.
- If no meaningful pattern can be identified, set "valid" to false.
"""


def load_intelligence_records():
    records = {}
    for json_file in DATASET_DIR.rglob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        metadata = data.get("metadata", {})
        intelligence_id = str(metadata.get("id", "")).strip()
        if not intelligence_id:
            continue

        domain = metadata.get("domain", "")
        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags]

        records[intelligence_id] = {
            "id": intelligence_id,
            "name": str(metadata.get("name", "")),
            "description": str(metadata.get("description", "")),
            "context": str(metadata.get("context", "")),
            "domain": str(domain),
            "tags": [str(tag) for tag in tags],
        }
    return records


def resolve_membership_file(path):
    if path.exists():
        return path

    # Prefer the highest-K generated membership file when the generic file is absent.
    candidates = sorted(
        path.parent.glob("fuzzy_membership_K*.csv"),
        key=lambda candidate: int(re.search(r"K(\d+)", candidate.stem).group(1)),
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return None


def load_clusters(path):
    membership = pd.read_csv(path, index_col=0)
    membership.index = membership.index.astype(str)
    membership = membership.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    is_binary = np.isin(membership.to_numpy(), [0.0, 1.0]).all()
    clusters = {}

    if ASSIGNMENT_MODE == "overlap" and is_binary:
        for cluster_name in membership.columns:
            member_ids = membership.index[membership[cluster_name] > 0].tolist()
            if member_ids:
                clusters[cluster_name] = member_ids
    else:
        assignments = membership.to_numpy().argmax(axis=1)
        for cluster_index, cluster_name in enumerate(membership.columns):
            member_ids = membership.index[assignments == cluster_index].tolist()
            if member_ids:
                clusters[cluster_name] = member_ids

    return clusters


def format_item(record):
    return (
        f"ID: {record['id']}\n"
        f"Name: {record['name']}\n"
        f"Description: {record['description']}\n"
        f"Context: {record['context']}\n"
        f"Domain: {record['domain']}\n"
        f"Tags: {', '.join(record['tags'])}"
    )


def parse_json_response(response_text):
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    result = json.loads(cleaned)

    if not isinstance(result, dict):
        raise ValueError("Ollama response is not a JSON object")

    evidence = result.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [str(evidence)]

    coherence = float(result.get("coherence", 0.0))
    return {
        "valid": bool(result.get("valid", False)),
        "insight": str(result.get("insight", "")),
        "evidence": [str(item) for item in evidence],
        "coherence": float(np.clip(coherence, 0.0, 1.0)),
        "reason": str(result.get("reason", "")),
    }


def analyze_cluster(approach, cluster_name, records):
    items_text = "\n\n--- ITEM ---\n\n".join(format_item(record) for record in records)
    prompt = (
        f"{ANALYSIS_PROMPT}\n\n"
        f"Approach: {approach}\n"
        f"Cluster: {cluster_name}\n"
        f"Number of items: {len(records)}\n\n"
        f"CLUSTER ITEMS:\n{items_text}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1},
    }

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
            return parse_json_response(body.get("response", "{}"))
        except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as error:
            last_error = error
            print(f"  Attempt {attempt + 1} failed for {cluster_name}: {error}")

    return {
        "valid": False,
        "insight": "",
        "evidence": [],
        "coherence": 0.0,
        "reason": f"LLM analysis failed: {last_error}",
    }


def main():
    if not OLLAMA_MODEL:
        raise ValueError("OLLAMA_MODEL is not set in the environment or .env file")

    records = load_intelligence_records()
    if not records:
        raise FileNotFoundError(f"No intelligence JSON records found in {DATASET_DIR}")

    print(f"Loaded {len(records)} intelligence records")
    print(f"Using Ollama model: {OLLAMA_MODEL}")

    for approach, configured_path in MEMBERSHIP_FILES.items():
        membership_path = resolve_membership_file(configured_path)
        if membership_path is None:
            print(f"Skipping {approach}: no membership CSV found")
            continue

        clusters = load_clusters(membership_path)
        approach_results = []
        print(f"\n--- Analyzing {approach} from {membership_path.name} ---")

        for cluster_name, member_ids in clusters.items():
            cluster_records = [records[item_id] for item_id in member_ids if item_id in records]
            missing_count = len(member_ids) - len(cluster_records)
            if not cluster_records:
                continue

            print(f"Analyzing {cluster_name}: {len(cluster_records)} items")
            result = analyze_cluster(approach, cluster_name, cluster_records)
            result.update({
                "approach": approach,
                "cluster": cluster_name,
                "item_count": len(cluster_records),
                "missing_items": missing_count,
                "membership_file": str(membership_path),
            })
            approach_results.append(result)

        json_path = OUTPUT_DIR / f"{approach}_cluster_insights.json"
        csv_path = OUTPUT_DIR / f"{approach}_cluster_insights.csv"
        json_path.write_text(json.dumps(approach_results, indent=2), encoding="utf-8")

        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "approach",
                    "cluster",
                    "item_count",
                    "missing_items",
                    "valid",
                    "coherence",
                    "insight",
                    "evidence",
                    "reason",
                    "membership_file",
                ],
            )
            writer.writeheader()
            for result in approach_results:
                row = result.copy()
                row["evidence"] = json.dumps(row["evidence"], ensure_ascii=False)
                writer.writerow(row)

        print(f"Saved {json_path}")
        print(f"Saved {csv_path}")


if __name__ == "__main__":
    main()
