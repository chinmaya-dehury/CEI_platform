import os
import glob
import warnings
import subprocess
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
import skfuzzy as fuzz
import networkx as nx

warnings.filterwarnings("ignore")

# ==========================================
# 1. PATHS & CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"
OUT_DIR = os.path.join(BASE_DIR, "results", "result_llm_pcm")
os.makedirs(OUT_DIR, exist_ok=True)

CSV_FILE = os.path.join(BASE_DIR, "similarity_results", "llm_experiment", "llm_similarity_matrix.csv")

if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(f"Similarity matrix CSV not found at: {CSV_FILE}")

print("Using similarity matrix:", CSV_FILE)

# ==========================================
# 2. LOAD & PREPROCESS SIMILARITY / DISTANCE
# ==========================================
df = pd.read_csv(CSV_FILE, index_col=0)
ids = df.index.astype(str).tolist()
S = df.values.astype(float)

S = np.nan_to_num(S, nan=0.0, posinf=1.0, neginf=0.0)
S = (S + S.T) / 2.0
S = np.clip(S, 0.0, 1.0)
np.fill_diagonal(S, 1.0)

N = len(S)
D = 1.0 - S

# Use Kernel/Relational Embedding (Gram Matrix) to avoid MDS projection loss
# Center the similarity matrix for Kernel PCA representation
H = np.eye(N) - np.ones((N, N)) / N
K_gram = -0.5 * H.dot(D ** 2).dot(H)
eigvals, eigvecs = np.linalg.eigh(K_gram)

# Keep positive spectral components
pos_idx = np.where(eigvals > 1e-5)[0]
X_rel = eigvecs[:, pos_idx] * np.sqrt(eigvals[pos_idx])


def fuzzy_silhouette(distance_matrix, membership):
    """Calculate a membership-weighted silhouette score."""
    scores = []
    for item_index in range(distance_matrix.shape[0]):
        own_cluster = int(np.argmax(membership[item_index]))
        own_weights = membership[:, own_cluster].copy()
        own_weights[item_index] = 0.0
        own_distance = (
            np.average(distance_matrix[item_index], weights=own_weights)
            if own_weights.sum() > 0 else 0.0
        )

        other_distances = []
        for cluster_index in range(membership.shape[1]):
            if cluster_index == own_cluster:
                continue
            weights = membership[:, cluster_index].copy()
            weights[item_index] = 0.0
            if weights.sum() > 0:
                other_distances.append(
                    np.average(distance_matrix[item_index], weights=weights)
                )

        if not other_distances:
            continue
        nearest_other = min(other_distances)
        denominator = max(own_distance, nearest_other)
        if denominator > 0:
            scores.append((nearest_other - own_distance) / denominator)

    return float(np.mean(scores)) if scores else np.nan

# 2. RUN CLUSTERING & EVALUATION
# Evaluate K from 2 through floor(N / 3).
K_RANGE = range(2, (N // 3) + 1)

results = []
membership_results = {}

for K in K_RANGE:
    # Standard Fuzzy C-Means
    centers, u, _, _, _, _, fpc = fuzz.cluster.cmeans( X_rel.T, c=K,  m=1.5,  error=0.005, maxiter=1000,   init=None,
    )
    U = u.T

    labels = np.argmax(U, axis=1)
    fuzzy_sil = fuzzy_silhouette(D, U)

    if len(np.unique(labels)) > 1:
        ord_sil = silhouette_score(D, labels, metric="precomputed")
        db = davies_bouldin_score(X_rel, labels)
        ch = calinski_harabasz_score(X_rel, labels)

    else:
        ord_sil = np.nan
        db = np.nan
        ch = np.nan

    results.append({"K": K, "fpc": fpc, "fuzzy_silhouette": fuzzy_sil, "silhouette_score": ord_sil, "ordinary_silhouette": ord_sil, "davies_bouldin": db, "calinski_harabasz": ch})
    membership_results[K] = U

results_df = pd.DataFrame(results)
print("\n--- Clustering Summary ---")
print(results_df.to_string(index=False))

best_metrics = {
    "fpc": (results_df.loc[results_df["fpc"].idxmax(), "K"], "max"),
    "fuzzy_silhouette": (results_df.loc[results_df["fuzzy_silhouette"].idxmax(), "K"], "max"),
    "ordinary_silhouette": (results_df.loc[results_df["ordinary_silhouette"].idxmax(), "K"], "max"),
    "davies_bouldin": (results_df.loc[results_df["davies_bouldin"].idxmin(), "K"], "min"),
    "calinski_harabasz": (results_df.loc[results_df["calinski_harabasz"].idxmax(), "K"], "max"),
}
print("\n--- Best K by Metric ---")
for metric, (best_k, direction) in best_metrics.items():
    value = results_df.loc[results_df["K"] == best_k, metric].iloc[0]
    print(f"{metric}: K={int(best_k)}, score={value:.6f} ({direction})")

# Use Fuzzy Silhouette as the primary K-selection metric.
best_k = int(best_metrics["fuzzy_silhouette"][0])
U_best = membership_results[best_k]
membership_df = pd.DataFrame(
    U_best,
    index=ids,
    columns=[f"Cluster_{k + 1}" for k in range(best_k)],
)
membership_df.to_csv(os.path.join(OUT_DIR, f"fuzzy_membership_K{best_k}.csv"))
membership_df.to_csv(os.path.join(OUT_DIR, "fuzzy_membership_matrix.csv"))
print(f"\nSaved fuzzy membership matrix for K={best_k}")

# 3. TRUE OVERLAPPING EXPERIMENT
OVERLAP_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]

overlap_results = []

for threshold in OVERLAP_THRESHOLDS:
    U = membership_results[best_k]
    U_overlap = (U >= threshold).astype(int)
    valid_clusters = np.where(U_overlap.sum(axis=0) >= 2)[0]
    U_overlap = U_overlap[:, valid_clusters]

    membership_count = U_overlap.sum(axis=1)
    overlap_results.append({
        "threshold": threshold,
        "K": best_k,
        "actual_clusters": U_overlap.shape[1],
        "overlap_ratio": np.mean(membership_count > 1),
        "average_cluster_memberships": np.mean(membership_count),
    })

    threshold_label = f"{threshold:.2f}".replace(".", "_")
    overlap_df = pd.DataFrame(
        U_overlap,
        index=ids,
        columns=[f"Cluster_{k + 1}" for k in valid_clusters],
    )
    overlap_df.to_csv(
        os.path.join(
            OUT_DIR,
            f"overlapping_membership_threshold_{threshold_label}_K{best_k}.csv",
        )
    )

    assignments = []
    for cluster_index, cluster_id in enumerate(valid_clusters):
        member_indexes = np.where(U[:, cluster_id] >= threshold)[0]
        for member_index in member_indexes:
            assignments.append({
                "threshold": threshold,
                "K": best_k,
                "cluster": f"Cluster_{cluster_index + 1}",
                "intelligence_id": ids[member_index],
                "membership": float(U[member_index, cluster_id]),
            })

    pd.DataFrame(assignments).to_csv(
        os.path.join(
            OUT_DIR,
            f"cluster_assignments_threshold_{threshold_label}_K{best_k}.csv",
        ),
        index=False,
    )

overlap_results_df = pd.DataFrame(overlap_results)
overlap_results_df.to_csv(
    os.path.join(OUT_DIR, "overlap_threshold_summary.csv"),
    index=False,
)
print("\n--- Overlapping Clustering Summary ---")
print(overlap_results_df.to_string(index=False))
print(f"\nSaved threshold assignments for K={best_k}")

for metric, title in {
    "fpc": "Fuzzy Partition Coefficient by K",
    "fuzzy_silhouette": "Fuzzy Silhouette Score by K",
    "silhouette_score": "Silhouette Score by K",
    "ordinary_silhouette": "Silhouette Score by K",
    "davies_bouldin": "Davies-Bouldin Index by K",
    "calinski_harabasz": "Calinski-Harabasz Index by K",
}.items():
    plt.figure(figsize=(8, 5))
    plt.plot(results_df["K"], results_df[metric], marker="o")
    plt.axvline(best_k, linestyle="--", label=f"Best K = {best_k}")
    plt.xlabel("Number of Clusters (K)")
    plt.ylabel(metric)
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"{metric}_vs_K.png"), dpi=300)
    plt.close()

print(f"Graphs saved to {OUT_DIR}")

# Run the Ollama-based cluster insight analysis after exporting assignments.
ANALYZER_PATH = os.path.join(
    BASE_DIR,
    "archive",
    "analyze_cluster_insights.py",
)
if os.path.exists(ANALYZER_PATH):
    print("\nRunning cluster insight analysis with Ollama...")
    subprocess.run([sys.executable, ANALYZER_PATH], check=True)