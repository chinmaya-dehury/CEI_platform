import os
import glob
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.manifold import MDS
from sklearn.metrics import silhouette_score, davies_bouldin_score
import skfuzzy as fuzz

warnings.filterwarnings("ignore")


# 1. PATHS


BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"

OUT_DIR = os.path.join(BASE_DIR, "results\\result_cosine_baseline")
os.makedirs(OUT_DIR, exist_ok=True)



# 2. LOAD FEATURE-BASED SIMILARITY MATRIX

csv_files = glob.glob(os.path.join(BASE_DIR, "**", "*.csv"), recursive=True)

# Select your feature-based similarity matrix here.
# Example: feature_similarity_matrix.csv
CSV_FILE = os.path.join(BASE_DIR, "similarity_results", "cosine_experiment","similarity_matrix.csv")

if CSV_FILE is None:
    raise FileNotFoundError( "Feature-based similarity CSV was not found.""Set CSV_FILE manually." )

print("Using similarity matrix:")
print(CSV_FILE)


# 3. READ MATRIX


df = pd.read_csv(CSV_FILE, index_col=0)

ids = df.index.astype(str).tolist()

S = df.values.astype(float)

# Remove numerical problems
S = np.nan_to_num(S, nan=0.0, posinf=1.0, neginf=0.0)

# Force symmetry
S = (S + S.T) / 2.0

# Similarity should normally be in [0,1]
S = np.clip(S, 0.0, 1.0)

# Self-similarity
np.fill_diagonal(S, 1.0)

N = len(S)

print(f"Number of intelligence items: {N}")


# 4. SIMILARITY -> DISTANCE


D = 1.0 - S

D = np.clip(D, 0.0, 1.0)

np.fill_diagonal(D, 0.0)



# 5. GRAPH REPRESENTATION USING MDS

# The similarity matrix is converted to a distance matrix.
# MDS provides coordinates representing the relationships between intelligence items.

# These coordinates are only a representation of the similarity graph and are not the original intelligence features.


mds = MDS( n_components=10, dissimilarity="precomputed", random_state=42, normalized_stress="auto")

X = mds.fit_transform(D)

print("MDS representation shape:", X.shape)


# 6. METRIC FUNCTIONS


def fuzzy_silhouette(X, membership):
    """
    Membership-weighted fuzzy silhouette.

    Higher values indicate better cluster structure.
    """

    N = X.shape[0]
    K = membership.shape[1]
    distances = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)

    scores = []

    for i in range(N):

        # Most strongly associated cluster
        own_cluster = np.argmax(membership[i])
        own_weights = membership[:, own_cluster].copy()
        own_weights[i] = 0.0
        a_i = np.average(distances[i], weights=own_weights) if own_weights.sum() else 0.0
        other_cluster_distances = []

        for k in range(K):

            if k == own_cluster:
                continue

            weights = membership[:, k].copy()
            weights[i] = 0.0
            if weights.sum():
                other_cluster_distances.append(np.average(distances[i], weights=weights))

        if not other_cluster_distances:
            continue

        b_i = min(other_cluster_distances)

        denominator = max(a_i, b_i)

        if denominator > 0:
            s_i = (b_i - a_i) / denominator
            scores.append(s_i)

    if not scores:
        return np.nan

    return float(np.mean(scores))


def xie_beni_index(X, membership, centers, m=2.0):
    """
    Xie-Beni validity index.

    Lower values are better.
    """

    N = X.shape[0]
    K = centers.shape[0]

    numerator = 0.0

    for k in range(K):
        distances = np.linalg.norm(X - centers[k], axis=1) ** 2
        numerator += np.sum((membership[:, k] ** m) * distances)

    center_distances = []

    for k in range(K):
        for j in range(k + 1, K):

            d = np.linalg.norm(centers[k] - centers[j]) ** 2
            center_distances.append(d)

    min_center_distance = min(center_distances)

    if min_center_distance == 0:
        return np.inf

    return float(numerator / (N * min_center_distance))


def kwon_index(X, membership, centers, m=2.0):
    """
    Kwon fuzzy clustering validity index.

    Lower values are better.
    """

    N = X.shape[0]
    K = centers.shape[0]

    global_center = np.mean(X, axis=0)

    compactness = 0.0

    for k in range(K):
        distances = np.linalg.norm(X - centers[k], axis=1) ** 2
        compactness += np.sum((membership[:, k] ** m) * distances)

    center_dispersion = (np.sum(np.linalg.norm( centers - global_center, axis=1) ** 2) / K )

    center_distances = []

    for k in range(K):
        for j in range(k + 1, K):
            center_distances.append(np.linalg.norm(centers[k] - centers[j]) ** 2)

    min_center_distance = min(center_distances)

    if min_center_distance == 0:
        return np.inf

    return float((compactness + center_dispersion) / min_center_distance)


# 7. RUN FUZZY C-MEANS FOR DIFFERENT K

results = []

membership_results = {}

for K in range(2, (N // 2) + 1):

    print(f"Running K = {K}")

    centers, membership, _, _, _, _, fpc = fuzz.cluster.cmeans( X.T, c=K, m=2.0, error=0.005, maxiter=1000, init=None)

    # membership shape:
    # K x N
    # Convert to:
    # N x K
    U = membership.T

    # Fuzzy Silhouette
    fs = fuzzy_silhouette( X, U)

    # Xie-Beni
    xb = xie_beni_index( X, U, centers)

    # Kwon
    kwon = kwon_index( X, U, centers)

    # Hard labels only for baseline

    labels = np.argmax(U, axis=1)
    if len(np.unique(labels)) > 1:
        db = davies_bouldin_score( X, labels)
        ordinary_silhouette = silhouette_score( X, labels)
    else:
        db = np.nan
        ordinary_silhouette = np.nan

    results.append({"K": K, "fuzzy_silhouette": fs, "xie_beni": xb, "kwon_index": kwon, "davies_bouldin": db, "ordinary_silhouette": ordinary_silhouette })
    membership_results[K] = U

# 8. SAVE RESULTS
results_df = pd.DataFrame(results)

results_df.to_csv( os.path.join( OUT_DIR, "clustering_metrics.csv"), index=False)

print("\nResults:")
print(results_df)


# 9. SELECT BEST K

# Main metric:
# Fuzzy Silhouette -> higher is better

best_k_by_metric = {
    "fuzzy_silhouette": int(results_df.loc[results_df["fuzzy_silhouette"].idxmax(), "K"]),
    "ordinary_silhouette": int(results_df.loc[results_df["ordinary_silhouette"].idxmax(), "K"]),
    "xie_beni": int(results_df.loc[results_df["xie_beni"].idxmin(), "K"]),
    "kwon_index": int(results_df.loc[results_df["kwon_index"].idxmin(), "K"]),
    "davies_bouldin": int(results_df.loc[results_df["davies_bouldin"].idxmin(), "K"]),
}

print("\nBest K and score by metric:")
for metric, best_k in best_k_by_metric.items():
    value = results_df.loc[results_df["K"] == best_k, metric].iloc[0]
    print(f"{metric}: K={best_k}, score={value:.6f}")

BEST_K = best_k_by_metric["fuzzy_silhouette"]


# 10. SAVE MEMBERSHIP MATRIX

U_best = membership_results[BEST_K]

membership_df = pd.DataFrame( U_best, index=ids, columns=[ f"Cluster_{k+1}" for k in range(BEST_K)])

membership_df.to_csv( os.path.join( OUT_DIR,"fuzzy_membership_matrix.csv" ))


# 11. PLOT METRICS
# Fuzzy Silhouette

plt.figure(figsize=(8, 5))

plt.plot( results_df["K"], results_df["fuzzy_silhouette"], marker="o")

plt.xlabel("Number of Clusters (K)")
plt.ylabel("Fuzzy Silhouette Score")
plt.title("Fuzzy Silhouette Score vs. Number of Clusters")

plt.grid(True)
plt.tight_layout()
plt.savefig( os.path.join(OUT_DIR,"fuzzy_silhouette_vs_K.png" ), dpi=300)
plt.close()


# Xie-Beni

plt.figure(figsize=(8, 5))

plt.plot(results_df["K"],results_df["xie_beni"], marker="o")

plt.xlabel("Number of Clusters (K)")
plt.ylabel("Xie-Beni Index")
plt.title("Xie-Beni Index vs. Number of Clusters")

plt.grid(True)
plt.tight_layout()

plt.savefig( os.path.join( OUT_DIR, "xie_beni_vs_K.png" ), dpi=300)
plt.close()


# Kwon

plt.figure(figsize=(8, 5))

plt.plot(results_df["K"], results_df["kwon_index"], marker="o")

plt.xlabel("Number of Clusters (K)")
plt.ylabel("Kwon Index")
plt.title("Kwon Index vs. Number of Clusters")

plt.grid(True)
plt.tight_layout()

plt.savefig( os.path.join( OUT_DIR, "kwon_index_vs_K.png" ), dpi=300)

plt.close()


# Davies-Bouldin

plt.figure(figsize=(8, 5))
plt.plot(results_df["K"], results_df["davies_bouldin"], marker="o")
plt.xlabel("Number of Clusters (K)")
plt.ylabel("Davies-Bouldin Index")
plt.title("Davies-Bouldin Index vs. Number of Clusters")

plt.grid(True)
plt.tight_layout()

plt.savefig(os.path.join( OUT_DIR, "davies_bouldin_vs_K.png"), dpi=300)

plt.close()


print("\nAll results saved to:")
print(OUT_DIR)