import argparse
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
    "fcm_cosine": RESULTS_DIR / "result_cosine_fcm" / "fuzzy_membership_matrix.csv",
    "baseline_llm": RESULTS_DIR / "result_llm_baseline" / "fuzzy_membership_matrix.csv",
    "fcm_llm_standard": RESULTS_DIR / "result_llm_fcm" / "fuzzy_membership_matrix.csv",
}

OVERLAP_ASSIGNMENT_DIRS = {
    "fcm_cosine": RESULTS_DIR / "result_cosine_fcm",
    "fcm_llm": RESULTS_DIR / "result_llm_fcm",
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

    # --- GRID & SPACING PARAMETERS ---
    GRID_STEP = 0.8     # Unified spacing between cluster grid centers (x and y)
    MAX_RADIUS = 0.40    # Reduced node ring radius so nodes stay tight and don't overlap text
    
    positions = {}
    cluster_centers = {}
    grid_width = max(1, int(np.ceil(np.sqrt(len(cluster_names)))))

    for cluster_index, cluster_name in enumerate(cluster_names):
        cluster_ids = [item_id for item_id in clusters[cluster_name] if item_id in records]
        grid_x = cluster_index % grid_width
        grid_y = cluster_index // grid_width
        
        # Calculate cluster center coordinate
        center = np.array([grid_x * GRID_STEP, -grid_y * GRID_STEP], dtype=float)
        cluster_centers[cluster_name] = center
        
        if len(cluster_ids) == 1:
            positions[cluster_ids[0]] = center
        else:
            # Scaled radius bounded at MAX_RADIUS
            radius = min(MAX_RADIUS, 0.22 + 0.015 * np.sqrt(len(cluster_ids)))
            angles = np.linspace(0, 2 * np.pi, len(cluster_ids), endpoint=False)
            for item_index, item_id in enumerate(cluster_ids):
                positions[item_id] = center + radius * np.array([
                    np.cos(angles[item_index]),
                    np.sin(angles[item_index]),
                ])

    # Dynamic figure size proportional to grid size
    grid_height = int(np.ceil(len(cluster_names) / grid_width))
    plt.figure(figsize=(grid_width * 2.8 + 2.0, grid_height * 2.6 + 1.0), dpi=160)

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
        node_size=200,          # Slightly reduced node size for clarity
        alpha=0.9,
        linewidths=0.3,
        edgecolors="black",
    )

    domain_handles = [
        Line2D([0], [0], marker="o", color="w", label=domain,
               markerfacecolor=color, markersize=9)
        for domain, color in DOMAIN_COLORS.items()
    ]

    # --- PLOT CLUSTER LABELS (EXACT CENTER MATCHing) ---
    for cluster_name, center in cluster_centers.items():
        plt.text(
            center[0],              # Uses exact cluster center x-coordinate
            center[1] - 0.35,       # Fixed vertical offset directly below the cluster
            cluster_name,
            ha="center",
            va="top",
            fontsize=10,
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "#555555", "alpha": 0.9, "pad": 3},
        )
        # Place legend inside the empty bottom-right cell (grid_x=2, grid_y=2)
        empty_cell_x = 2 * GRID_STEP
        empty_cell_y = -2 * GRID_STEP

        plt.legend(
            handles=domain_handles,
            title="Application Domain",
            fontsize=13,
            title_fontsize=14,
            loc="center",
            bbox_to_anchor=(empty_cell_x, empty_cell_y),
            bbox_transform=plt.gca().transData,  # Uses data coordinates to lock position into the cell
            frameon=True,
            facecolor="white",
            edgecolor="#cccccc"
        )
    plt.title( f"Domain Distribution Across {len(clusters)} Clusters ({approach.capitalize()})",
    fontsize=14,          # Increases font size (e.g., 14 or 16 for titles)
    fontweight="bold",    # Makes title bold
    loc="center",          # Keeps title centered
    y=0.95
)
    plt.axis("off")
    plt.tight_layout(rect=(0, 0, 0.86, 1))
    graph_path = OUTPUT_DIR / f"{approach}_cluster_domain_graph.png"
    plt.savefig(graph_path, dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{approach}_cluster_domain_graph.pdf", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved graph {graph_path}")


def save_cluster_size_chart(approach, clusters, records):
    cluster_names = list(clusters)
    sizes = [
        sum(item_id in records for item_id in clusters[cluster_name])
        for cluster_name in cluster_names
    ]
    figure_width = max(10, len(cluster_names) * 0.7)
    plt.figure(figsize=(figure_width, 6), dpi=160)
    bars = plt.bar(cluster_names, sizes, color="#2878b5")
    for bar, size in zip(bars, sizes):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(size),
            ha="center",
            va="bottom",
        )
    plt.xlabel("Cluster")
    plt.ylabel("Items with available records")
    plt.title(f"{approach}: {len(cluster_names)} clusters and item counts")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    chart_path = OUTPUT_DIR / f"{approach}_cluster_sizes.png"
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{approach}_cluster_sizes.pdf", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved cluster-size chart {chart_path}")


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
    save_cluster_size_chart(approach, clusters, records)

    # LLM cluster analysis is disabled. Graphs and cluster-size reports still run.

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
    parser = argparse.ArgumentParser(description="Analyze clusters with Ollama")
    parser.add_argument("--membership-file", type=Path)
    parser.add_argument("--assignments-file", type=Path)
    parser.add_argument("--approach", default="fcm")
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()

    # Ollama calls are disabled; OLLAMA_MODEL is not required.

    records = load_records()
    if not records:
        raise FileNotFoundError(f"No intelligence JSON files found in {DATASET_DIR}")

    if args.membership_file and args.assignments_file:
        raise ValueError("Use only one of --membership-file or --assignments-file")

    if args.assignments_file:
        assignment_path = args.assignments_file.resolve()
        if not assignment_path.exists():
            raise FileNotFoundError(f"Assignment file not found: {assignment_path}")
        if args.plot_only:
            clusters = clusters_from_assignments(assignment_path)
            save_cluster_domain_graph(args.approach, clusters, records)
            save_cluster_size_chart(args.approach, clusters, records)
            return
        analyze_source(args.approach, assignment_path, clusters_from_assignments, records)
        return

    if args.membership_file:
        membership_path = args.membership_file.resolve()
        if not membership_path.exists():
            raise FileNotFoundError(f"Membership file not found: {membership_path}")
        if args.plot_only:
            clusters = clusters_from_membership(membership_path)
            save_cluster_domain_graph(args.approach, clusters, records)
            save_cluster_size_chart(args.approach, clusters, records)
            return
        analyze_source(args.approach, membership_path, clusters_from_membership, records)
        return

    for approach, path in STANDARD_MEMBERSHIP_FILES.items():
        if path.exists():
            analyze_source(approach, path, clusters_from_membership, records)


if __name__ == "__main__":
    main()
