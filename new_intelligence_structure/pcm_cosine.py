import os
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import silhouette_score, davies_bouldin_score
import skfuzzy as fuzz

warnings.filterwarnings("ignore")

# ==========================================
# 1. PATHS & CONFIGURATION
# ==========================================
BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"
OUT_DIR = os.path.join(BASE_DIR, "results\\result_cosine_pcm")

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
results = []
membership_results = {}

# Threshold for multi-cluster assignment (e.g., items can belong to multiple clusters if membership > 1/K)
for K in range(2, (N // 2) + 1):
    # Fuzzy C-Means on spectral relational features
    centers, u, _, _, _, _, fpc = fuzz.cluster.cmeans(
        X_rel.T, c=K, m=1.5, error=0.005, maxiter=1000, init=None
    )
    U = u.T  # Shape: (N, K)

    # Convert probabilistic FCM memberships to overlapping degrees:
    # Scale by K so average membership intensity stays comparable across different K
    U_overlapping = np.clip(U * (K / 2.0), 0.0, 1.0)

    # Primary cluster labels for evaluation
    labels = np.argmax(U, axis=1)
    
    unique_labels = len(np.unique(labels))
    if unique_labels > 1:
        db = davies_bouldin_score(D, labels)
        ord_sil = silhouette_score(D, labels, metric='precomputed')
    else:
        db, ord_sil = np.nan, np.nan

    results.append({
        "K": K,
        "fpc": fpc,
        "ordinary_silhouette": ord_sil,
        "davies_bouldin": db
    })
    membership_results[K] = U_overlapping

results_df = pd.DataFrame(results)
print("\n--- Clustering Summary ---")
print(results_df.to_string(index=False))

best_metrics = {
    "fpc": (results_df.loc[results_df["fpc"].idxmax(), "K"], "max"),
    "ordinary_silhouette": (results_df.loc[results_df["ordinary_silhouette"].idxmax(), "K"], "max"),
    "davies_bouldin": (results_df.loc[results_df["davies_bouldin"].idxmin(), "K"], "min"),
}
print("\n--- Best K by Metric ---")
for metric, (best_k, direction) in best_metrics.items():
    value = results_df.loc[results_df["K"] == best_k, metric].iloc[0]
    print(f"{metric}: K={int(best_k)}, score={value:.6f} ({direction})")

# Select Best K using standard relational silhouette score
valid_sil = results_df.dropna(subset=["ordinary_silhouette"])
if not valid_sil.empty:
    best_k = int(valid_sil.loc[valid_sil["ordinary_silhouette"].idxmax(), "K"])
    print(f"\nOptimal K based on Relational Silhouette: K = {best_k}")

    # Save overlapping membership matrix for optimal K
    U_best = membership_results[best_k]
    membership_df = pd.DataFrame(
        U_best, 
        index=ids, 
        columns=[f"Cluster_{k+1}" for k in range(best_k)]
    )
    membership_df.to_csv(os.path.join(OUT_DIR, f"overlapping_membership_K{best_k}.csv"))
    print(f"Saved overlapping memberships to {OUT_DIR}")

for metric, title in {
    "fpc": "Fuzzy Partition Coefficient by K",
    "ordinary_silhouette": "Ordinary Silhouette by K",
    "davies_bouldin": "Davies-Bouldin Index by K",
}.items():
    plt.figure(figsize=(8, 5))
    plt.plot(results_df["K"], results_df[metric], marker="o")
    plt.xlabel("Number of Clusters (K)")
    plt.ylabel(metric)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"{metric}_vs_K.png"), dpi=300)
    plt.close()

print(f"Graphs saved to {OUT_DIR}")