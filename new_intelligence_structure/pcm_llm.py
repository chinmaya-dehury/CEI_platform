import os
import glob
import warnings
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

# 2. RUN CLUSTERING & EVALUATION
# 8 application domains -> evaluate K = 2 to 8
K_RANGE = range(2, 9)

results = []
membership_results = {}

for K in K_RANGE:
    # Standard Fuzzy C-Means
    centers, u, _, _, _, _, fpc = fuzz.cluster.cmeans( X_rel.T, c=K,  m=1.5,  error=0.005, maxiter=1000,   init=None,
    )
    U = u.T

    labels = np.argmax(U, axis=1)

    if len(np.unique(labels)) > 1:
        ord_sil = silhouette_score(D, labels, metric="precomputed")
        db = davies_bouldin_score(X_rel, labels)
        ch = calinski_harabasz_score(X_rel, labels)

        wss = 0.0
        for cluster_id in range(K):
            members = np.where(labels == cluster_id)[0]
            if len(members) > 0:
                centroid = centers[cluster_id]
                wss += np.sum((X_rel[members] - centroid) ** 2)
    else:
        ord_sil = np.nan
        db = np.nan
        ch = np.nan
        wss = np.nan

    results.append({"K": K,"fpc": fpc, "ordinary_silhouette": ord_sil,  "davies_bouldin": db,  "calinski_harabasz": ch,  "wss": wss, })
    membership_results[K] = U

results_df = pd.DataFrame(results)
print("\n--- Clustering Summary ---")
print(results_df.to_string(index=False))

best_metrics = {
    "fpc": (results_df.loc[results_df["fpc"].idxmax(), "K"], "max"),
    "ordinary_silhouette": (results_df.loc[results_df["ordinary_silhouette"].idxmax(), "K"], "max"),
    "davies_bouldin": (results_df.loc[results_df["davies_bouldin"].idxmin(), "K"], "min"),
    "calinski_harabasz": (results_df.loc[results_df["calinski_harabasz"].idxmax(), "K"], "max"),
    "wss": (results_df.loc[results_df["wss"].idxmin(), "K"], "min"),
}
print("\n--- Best K by Metric ---")
for metric, (best_k, direction) in best_metrics.items():
    value = results_df.loc[results_df["K"] == best_k, metric].iloc[0]
    print(f"{metric}: K={int(best_k)}, score={value:.6f} ({direction})")

# Use the 8-domain assumption for the domain-aligned fuzzy clustering result.
best_k = 8
U_best = membership_results[best_k]
membership_df = pd.DataFrame(
    U_best,
    index=ids,
    columns=[f"Cluster_{k + 1}" for k in range(best_k)],
)
membership_df.to_csv(os.path.join(OUT_DIR, f"fuzzy_membership_K{best_k}.csv"))
print(f"\nSaved fuzzy membership matrix for K={best_k}")

# 3. TRUE OVERLAPPING EXPERIMENT
OVERLAP_THRESHOLD = 0.40

overlap_results = []
overlap_membership_results = {}

for K in K_RANGE:
    # Start from FCM only to obtain initial membership strength.
    centers, u, _, _, _, _, _ = fuzz.cluster.cmeans( X_rel.T, c=K, m=1.5,  error=0.005, maxiter=1000, init=None,)
    U = u.T

    U_overlap = (U >= OVERLAP_THRESHOLD).astype(int)
    valid_clusters = np.where(U_overlap.sum(axis=0) >= 2)[0]
    U_overlap = U_overlap[:, valid_clusters]
    overlap_membership_results[K] = U_overlap

    G = nx.Graph()
    G.add_nodes_from(range(N))
    for i in range(N):
        for j in range(i + 1, N):
            if S[i, j] > 0:
                G.add_edge(i, j, weight=float(S[i, j]))

    membership_count = U_overlap.sum(axis=1)
    overlap_results.append({
        "K": K,
        "actual_clusters": U_overlap.shape[1],
        "overlap_ratio": np.mean(membership_count > 1),
        "average_cluster_memberships": np.mean(membership_count),
    })

overlap_results_df = pd.DataFrame(overlap_results)
print("\n--- Overlapping Clustering Summary ---")
print(overlap_results_df.to_string(index=False))

U_overlap_best = overlap_membership_results[8]
overlap_df = pd.DataFrame(
    U_overlap_best,
    index=ids,
    columns=[f"Cluster_{k + 1}" for k in range(U_overlap_best.shape[1])],
)
overlap_df.to_csv(os.path.join(OUT_DIR, "overlapping_membership_K8.csv"))
print("\nSaved overlapping membership matrix for K=8")

for metric, title in {
    "fpc": "Fuzzy Partition Coefficient by K",
    "ordinary_silhouette": "Silhouette Score by K",
    "davies_bouldin": "Davies-Bouldin Index by K",
    "calinski_harabasz": "Calinski-Harabasz Index by K",
    "wss": "Within-Cluster Sum of Squares by K",
}.items():
    plt.figure(figsize=(8, 5))
    plt.plot(results_df["K"], results_df[metric], marker="o")
    plt.axvline(8, linestyle="--", label="K = 8")
    plt.xlabel("Number of Clusters (K)")
    plt.ylabel(metric)
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"{metric}_vs_K.png"), dpi=300)
    plt.close()

print(f"Graphs saved to {OUT_DIR}")