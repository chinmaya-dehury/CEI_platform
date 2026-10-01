import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "dataset"
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_DIR = RESULTS_DIR / "cluster_insights"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STANDARD_MEMBERSHIP_FILES = {
    "baseline_llm": RESULTS_DIR / "result_llm_baseline" / "fuzzy_membership_matrix.csv",
    "fcm_llm_standard": RESULTS_DIR / "result_llm_fcm" / "fuzzy_membership_matrix.csv",
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
        records[item_id] = {"id": item_id, "domain": str(metadata.get("domain", ""))}
    return records

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
    return {
        str(cluster_name): group["intelligence_id"].astype(str).tolist()
        for cluster_name, group in assignments.groupby("cluster", sort=False)
    }

def save_cluster_domain_graph(approach, clusters, records):
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
                    graph.add_edge(left_id, right_id, weight=1, color=edge_colors[cluster_index])

    if not graph.nodes:
        return

    GRID_STEP, MAX_RADIUS, grid_width = 0.9, 0.28, 7
    positions, cluster_centers = {}, {}

    for cluster_index, cluster_name in enumerate(cluster_names):
        cluster_ids = [item_id for item_id in clusters[cluster_name] if item_id in records]
        grid_x, grid_y = cluster_index % grid_width, cluster_index // grid_width
        center = np.array([grid_x * GRID_STEP, -grid_y * GRID_STEP], dtype=float)
        cluster_centers[cluster_name] = center
        
        if len(cluster_ids) == 1:
            positions[cluster_ids[0]] = center
        else:
            radius = min(MAX_RADIUS, 0.22 + 0.015 * np.sqrt(len(cluster_ids)))
            angles = np.linspace(0, 2 * np.pi, len(cluster_ids), endpoint=False)
            for item_index, item_id in enumerate(cluster_ids):
                positions[item_id] = center + radius * np.array([np.cos(angles[item_index]), np.sin(angles[item_index])])

    grid_height = int(np.ceil(len(cluster_names) / grid_width))
    plt.figure(figsize=(12, max(8, grid_height * 1.8)), dpi=160)
    node_colors = [DOMAIN_COLORS.get(records[node]["domain"], "#7f7f7f") for node in graph.nodes]

    nx.draw_networkx_edges(
        graph, positions,
        edge_color=[data.get("color", "#aaaaaa") for _, _, data in graph.edges(data=True)],
        alpha=0.18, width=[0.5 + data.get("weight", 1) for _, _, data in graph.edges(data=True)]
    )
    nx.draw_networkx_nodes(
        graph, positions, node_color=node_colors, node_size=200, alpha=0.9, linewidths=0.3, edgecolors="black"
    )

    domain_handles = [
        Line2D([0], [0], marker="o", color="w", label=domain, markerfacecolor=color, markersize=9)
        for domain, color in DOMAIN_COLORS.items()
    ]

    for cluster_name, center in cluster_centers.items():
        plt.text(
            center[0], center[1] - 0.35, cluster_name, ha="center", va="top",
            fontsize=10, fontweight="bold", bbox={"facecolor": "white", "edgecolor": "#555555", "alpha": 0.9, "pad": 3}
        )

    plt.legend(
        handles=domain_handles, title="Application Domain", fontsize=13, title_fontsize=15,
        loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=4, frameon=True, facecolor="white", edgecolor="#cccccc"
    )
    plt.title(
        f"Domain Distribution Across {len(clusters)} Clusters ({approach.capitalize()})",
        fontsize=20, fontweight="bold", loc="center", y=0.95
    )
    plt.axis("off")
    plt.tight_layout(rect=(0, 0.14, 1, 1))

    graph_path = OUTPUT_DIR / f"{approach}_cluster_domain_graph.png"
    plt.savefig(graph_path, dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{approach}_cluster_domain_graph.pdf", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved graph {graph_path}")

def save_cluster_size_chart(approach, clusters, records):
    cluster_names = list(clusters)
    sizes = [sum(item_id in records for item_id in clusters[cluster_name]) for cluster_name in cluster_names]
    plt.figure(figsize=(max(10, len(cluster_names) * 0.7), 6), dpi=160)
    bars = plt.bar(cluster_names, sizes, color="#2878b5")
    
    for bar, size in zip(bars, sizes):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(size), ha="center", va="bottom")
        
    plt.xlabel("Cluster")
    plt.ylabel("Items with available records")
    plt.title(f"{approach}: {len(cluster_names)} clusters and item counts")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout(rect=(0, 0, 1, 0.98))

    chart_path = OUTPUT_DIR / f"{approach}_cluster_sizes.png"
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / f"{approach}_cluster_sizes.pdf", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved cluster-size chart {chart_path}")

def generate_plots(approach, path, cluster_loader, records):
    clusters = cluster_loader(path)
    print(f"\nProcessing {approach}: {path.name}")
    save_cluster_domain_graph(approach, clusters, records)
    save_cluster_size_chart(approach, clusters, records)

def main():
    parser = argparse.ArgumentParser(description="Generate cluster plots")
    parser.add_argument("--membership-file", type=Path)
    parser.add_argument("--assignments-file", type=Path)
    parser.add_argument("--approach", default="fcm")
    args = parser.parse_args()

    records = load_records()
    if not records:
        raise FileNotFoundError(f"No intelligence JSON files found in {DATASET_DIR}")

    if args.membership_file and args.assignments_file:
        raise ValueError("Use only one of --membership-file or --assignments-file")

    if args.assignments_file:
        path = args.assignments_file.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Assignment file not found: {path}")
        generate_plots(args.approach, path, clusters_from_assignments, records)
        return

    if args.membership_file:
        path = args.membership_file.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Membership file not found: {path}")
        generate_plots(args.approach, path, clusters_from_membership, records)
        return

    for approach, path in STANDARD_MEMBERSHIP_FILES.items():
        if path.exists():
            generate_plots(approach, path, clusters_from_membership, records)

if __name__ == "__main__":
    main()