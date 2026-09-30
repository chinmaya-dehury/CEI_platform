import csv
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
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
MAX_RETRIES = 2

STANDARD_MEMBERSHIP_FILES = {
    "baseline_cosine": RESULTS_DIR / "result_cosine_baseline_corrected" / "fuzzy_membership_matrix.csv",
    "pcm_cosine": RESULTS_DIR / "result_cosine_pcm" / "fuzzy_membership_matrix.csv",
    "baseline_llm": RESULTS_DIR / "result_llm_baseline" / "fuzzy_membership_matrix.csv",
    "pcm_llm_standard": RESULTS_DIR / "result_llm_pcm" / "fuzzy_membership_matrix.csv",
}

OVERLAP_ASSIGNMENT_DIRS = {
    "pcm_cosine": RESULTS_DIR / "result_cosine_pcm",
    "pcm_llm": RESULTS_DIR / "result_llm_pcm",
}

DOMAIN_COLORS = {
    "Transportation": "#1f77b4",
    "Agriculture": "#2ca02c",
    "Manufacturing": "#ff7f0e",
    "Healthcare": "#d62728",
    "Environment": "#17becf",
    "Energy": "#bcbd22",
    "Smart Building": "#9467bd",
    "Disaster Management": "#8c564b",
}

PROMPT = """You are a cluster-insight analyst.

You will receive the items belonging to ONE cluster.

Tasks:
1. Identify the main common theme, behavior, capability, or characteristic shared by the items.
2. Explain the key insight represented by this cluster in 1-3 sentences.
3. Identify the strongest evidence from the items supporting the insight.
4. Check whether the items are sufficiently coherent or appear unrelated.
5. Decide whether the cluster is meaningful based on its internal pattern.

Return ONLY this JSON object:
{
  "valid": true,
  "insight": "short description of the discovered pattern",
  "evidence": ["key evidence 1", "key evidence 2"],
  "coherence": 0.0,
  "reason": "short explanation"
}

Do not invent information. Do not judge the cluster based only on similarity. Set valid to false if no meaningful pattern can be identified.
"""


def load_records():
    records = {}
    for path in DATASET_DIR.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        metadata = data.get("metadata", {})
        item_id = str(metadata.get("id", "")).strip()
        if not item_id:
            continue

        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags]

        records[item_id] = {
            "id": item_id,
            "name": str(metadata.get("name", "")),
            "description": str(metadata.get("description", "")),
            "context": str(metadata.get("context", "")),
            "domain": str(metadata.get("domain", "")),
            "tags": ", ".join(str(tag) for tag in tags),
        }
    return records


def item_text(item):
    return (
        f"ID: {item['id']}\n"
        f"Name: {item['name']}\n"
        f"Description: {item['description']}\n"
        f"Context: {item['context']}\n"
        f"Domain: {item['domain']}\n"
        f"Tags: {item['tags']}"
    )


def clusters_from_membership(path):
    membership = pd.read_csv(path, index_col=0)
    membership.index = membership.index.astype(str)
    membership = membership.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    assignments = membership.to_numpy().argmax(axis=1)
    return {
        cluster_name: membership.index[assignments == index].tolist()
        for index, cluster_name in enumerate(membership.columns)
        if np.any(assignments == index)
    }


def clusters_from_assignments(path):
    assignments = pd.read_csv(path)
    required = {"cluster", "intelligence_id"}
    if not required.issubset(assignments.columns):
        raise ValueError(f"Missing columns in {path}: {required - set(assignments.columns)}")

    clusters = {}
    for cluster_name, group in assignments.groupby("cluster", sort=False):
        clusters[str(cluster_name)] = group["intelligence_id"].astype(str).tolist()
    return clusters


def save_cluster_domain_graph(approach, clusters, records):
    """Save a graph with domain-colored nodes and cluster-colored edges."""
    member_ids = sorted({item_id for ids in clusters.values() for item_id in ids})
    graph = nx.Graph()
    graph.add_nodes_from(item_id for item_id in member_ids if item_id in records)

    cluster_names = list(clusters)
    edge_colors = plt.cm.hsv(np.linspace(0, 1, max(len(cluster_names), 1), endpoint=False))
    for cluster_index, cluster_name in enumerate(cluster_names):
        cluster_ids = [item_id for item_id in clusters[cluster_name] if item_id in records]
        for left_index, left_id in enumerate(cluster_ids):
            for right_id in cluster_ids[left_index + 1:]:
                if graph.has_edge(left_id, right_id):
                    graph[left_id][right_id]["weight"] += 1
                else:
                    graph.add_edge(
                        left_id,
                        right_id,
                        weight=1,
                        color=edge_colors[cluster_index],
                    )

    if not graph.nodes:
        return

    positions = nx.spring_layout(graph, seed=42, k=1.2 / np.sqrt(len(graph.nodes)))
    plt.figure(figsize=(16, 12))
    node_colors = [
        DOMAIN_COLORS.get(records[node]["domain"], "#7f7f7f")
        for node in graph.nodes
    ]
    nx.draw_networkx_edges(
        graph,
        positions,
        edge_color=[data.get("color", "#aaaaaa") for _, _, data in graph.edges(data=True)],
        alpha=0.18,
        width=[0.5 + data.get("weight", 1) for _, _, data in graph.edges(data=True)],
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        node_color=node_colors,
        node_size=90,
        alpha=0.9,
        linewidths=0.3,
        edgecolors="black",
    )

    domain_handles = [
        Line2D([0], [0], marker="o", color="w", label=domain,
               markerfacecolor=color, markersize=9)
        for domain, color in DOMAIN_COLORS.items()
    ]
    plt.legend(handles=domain_handles, title="Application domain", loc="upper left")
    plt.title(f"{approach}: cluster relationships with domain-colored intelligences")
    plt.axis("off")
    plt.tight_layout()
    graph_path = OUTPUT_DIR / f"{approach}_cluster_domain_graph.png"
    plt.savefig(graph_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved graph {graph_path}")


def parse_response(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    result = json.loads(text)
    coherence = float(np.clip(float(result.get("coherence", 0.0)), 0.0, 1.0))
    evidence = result.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [evidence]
    return {
        "valid": bool(result.get("valid", False)),
        "insight": str(result.get("insight", "")),
        "evidence": [str(value) for value in evidence],
        "coherence": coherence,
        "reason": str(result.get("reason", "")),
    }


def analyze_cluster(approach, cluster_name, items):
    prompt = (
        f"{PROMPT}\n\nApproach: {approach}\n"
        f"Cluster: {cluster_name}\nNumber of items: {len(items)}\n\n"
        + "\n\n--- ITEM ---\n\n".join(item_text(item) for item in items)
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1},
    }

    error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            return parse_response(response.json().get("response", "{}"))
        except (requests.RequestException, json.JSONDecodeError, ValueError, TypeError) as exc:
            error = exc
            print(f"  Attempt {attempt + 1} failed for {cluster_name}: {exc}")

    return {
        "valid": False,
        "insight": "",
        "evidence": [],
        "coherence": 0.0,
        "reason": f"LLM analysis failed: {error}",
    }


def analyze_source(approach, path, cluster_loader, records):
    clusters = cluster_loader(path)
    results = []
    print(f"\nAnalyzing {approach}: {path.name}")
    save_cluster_domain_graph(approach, clusters, records)

    for cluster_name, item_ids in clusters.items():
        items = [records[item_id] for item_id in item_ids if item_id in records]
        if not items:
            continue
        print(f"  {cluster_name}: {len(items)} items")
        result = analyze_cluster(approach, cluster_name, items)
        result.update({
            "approach": approach,
            "cluster": cluster_name,
            "item_count": len(items),
            "missing_items": len(item_ids) - len(items),
            "source_file": str(path),
        })
        results.append(result)

    output_json = OUTPUT_DIR / f"{approach}_cluster_insights.json"
    output_csv = OUTPUT_DIR / f"{approach}_cluster_insights.csv"
    output_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    with output_csv.open("w", newline="", encoding="utf-8") as file:
        fields = [
            "approach", "cluster", "item_count", "missing_items", "valid",
            "coherence", "insight", "evidence", "reason", "source_file",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = result.copy()
            row["evidence"] = json.dumps(row["evidence"], ensure_ascii=False)
            writer.writerow(row)

    print(f"  Saved {output_json}")
    print(f"  Saved {output_csv}")


def main():
    if not OLLAMA_MODEL:
        raise ValueError("OLLAMA_MODEL is not set in the environment or .env file")

    records = load_records()
    if not records:
        raise FileNotFoundError(f"No intelligence JSON files found in {DATASET_DIR}")

    for approach, path in STANDARD_MEMBERSHIP_FILES.items():
        if path.exists():
            analyze_source(approach, path, clusters_from_membership, records)
        else:
            print(f"Skipping missing file: {path}")

    for source_name, assignment_dir in OVERLAP_ASSIGNMENT_DIRS.items():
        for path in sorted(assignment_dir.glob("cluster_assignments_threshold_*.csv")):
            threshold_match = re.search(r"threshold_(\d+_\d+)_K(\d+)", path.stem)
            threshold = threshold_match.group(1).replace("_", ".") if threshold_match else "unknown"
            approach = f"{source_name}_overlap_threshold_{threshold}"
            analyze_source(approach, path, clusters_from_assignments, records)


if __name__ == "__main__":
    main()
