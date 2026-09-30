import os
import subprocess
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import skfuzzy as fuzz

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)

warnings.filterwarnings("ignore")


# ============================================================
# 1. PATHS & CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"

OUT_DIR = os.path.join(
    BASE_DIR,
    "results",
    "result_cosine_pcm"
)

CSV_FILE = os.path.join(
    BASE_DIR,
    "similarity_results",
    "cosine_experiment",
    "similarity_matrix.csv"
)

os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(
        f"Similarity matrix CSV not found at:\n{CSV_FILE}"
    )

print("=" * 70)
print("FUZZY CLUSTERING PIPELINE")
print("=" * 70)
print("Using similarity matrix:")
print(CSV_FILE)


# ============================================================
# 2. CONFIGURATION
# ============================================================

# K range is set after loading N so it remains valid if the dataset changes.
MIN_K = 2

# Fuzzy exponent.
# m=1.5 gives somewhat sharper memberships than m=2.
FUZZINESS_M = 1.5

# Number of independent FCM restarts per K.
N_RESTARTS = 20

# FCM convergence parameters.
ERROR = 1e-6
MAXITER = 2000

# Reproducibility.
RANDOM_SEED = 42

# Thresholds used for the post-hoc overlapping representation.
OVERLAP_THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]

# If True, standardize the spectral coordinates before FCM.
# This often prevents one spectral dimension from dominating.
STANDARDIZE_FEATURES = True


# ============================================================
# 3. LOAD SIMILARITY MATRIX
# ============================================================

df = pd.read_csv(CSV_FILE, index_col=0)

ids = df.index.astype(str).tolist()

S = df.values.astype(float)

if S.shape[0] != S.shape[1]:
    raise ValueError(
        f"Similarity matrix must be square. Found shape: {S.shape}"
    )

N = S.shape[0]

if len(ids) != N:
    raise ValueError("Number of IDs does not match similarity matrix.")


# ============================================================
# 4. CLEAN SIMILARITY MATRIX
# ============================================================

# Replace invalid values.
S = np.nan_to_num(
    S,
    nan=0.0,
    posinf=0.0,
    neginf=0.0
)

# Symmetrize.
S = (S + S.T) / 2.0

# Force self-similarity to 1.
np.fill_diagonal(S, 1.0)

print("\n" + "=" * 70)
print("SIMILARITY DIAGNOSTICS")
print("=" * 70)

print(f"N items       : {N}")
print(f"Minimum       : {S.min():.8f}")
print(f"Maximum       : {S.max():.8f}")
print(f"Mean          : {S.mean():.8f}")
print(f"Median        : {np.median(S):.8f}")
print(f"Std           : {S.std():.8f}")

# Important validation.
if np.min(S) < -1.000001 or np.max(S) > 1.000001:
    print(
        "\nWARNING: Similarity values are outside [-1, 1]."
        "\nCheck the input matrix before clustering."
    )

# Similarity distribution excluding diagonal.
off_diag = S[~np.eye(N, dtype=bool)]

print("\nOff-diagonal similarity:")
print(f"Minimum       : {off_diag.min():.8f}")
print(f"Maximum       : {off_diag.max():.8f}")
print(f"Mean          : {off_diag.mean():.8f}")
print(f"Median        : {np.median(off_diag):.8f}")
print(f"Std           : {off_diag.std():.8f}")

print("\nPercentiles:")
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"{p:>3}%           : {np.percentile(off_diag, p):.8f}")


# ============================================================
# 5. CONVERT SIMILARITY TO DISTANCE
# ============================================================

# For cosine-style similarity:
#
#       D(i,j) = 1 - S(i,j)
#
# If S is in [-1,1], D is in [0,2].
#
# Do NOT clip D to [0,1].

D = 1.0 - S

D = (D + D.T) / 2.0

np.fill_diagonal(D, 0.0)

print("\n" + "=" * 70)
print("DISTANCE DIAGNOSTICS")
print("=" * 70)

print(f"Minimum       : {D.min():.8f}")
print(f"Maximum       : {D.max():.8f}")
print(f"Mean          : {D.mean():.8f}")
print(f"Median        : {np.median(D):.8f}")
print(f"Std           : {D.std():.8f}")


# ============================================================
# 6. SPECTRAL / RELATIONAL EMBEDDING
# ============================================================

print("\n" + "=" * 70)
print("RELATIONAL EMBEDDING")
print("=" * 70)

H = np.eye(N) - np.ones((N, N)) / N

# Classical multidimensional scaling / distance-based Gram matrix.
K_gram = -0.5 * H @ (D ** 2) @ H

# Numerical symmetry.
K_gram = (K_gram + K_gram.T) / 2.0

eigvals, eigvecs = np.linalg.eigh(K_gram)

# Sort descending.
order = np.argsort(eigvals)[::-1]

eigvals = eigvals[order]
eigvecs = eigvecs[:, order]

positive_mask = eigvals > 1e-8

positive_eigvals = eigvals[positive_mask]
positive_eigvecs = eigvecs[:, positive_mask]

if len(positive_eigvals) == 0:
    raise ValueError(
        "No positive eigenvalues were found. "
        "The similarity/distance matrix cannot produce a usable "
        "positive spectral embedding."
    )

# Use all positive dimensions initially.
X_rel = (
    positive_eigvecs
    * np.sqrt(positive_eigvals)
)

print(f"Positive dimensions: {X_rel.shape[1]}")
print(f"Largest eigenvalue : {positive_eigvals[0]:.8f}")
print(f"Smallest positive : {positive_eigvals[-1]:.8f}")

negative_eigenvalues = eigvals[eigvals < -1e-8]

print(f"Negative eigenvalues: {len(negative_eigenvalues)}")

if len(negative_eigenvalues) > 0:
    print(
        "Note: the original distance geometry is not perfectly Euclidean."
    )


# ============================================================
# 7. LIMIT EMBEDDING DIMENSION
# ============================================================

# Avoid feeding an unnecessarily huge number of dimensions into FCM.
MAX_EMBED_DIM = min(20, X_rel.shape[1])

X_rel = X_rel[:, :MAX_EMBED_DIM]

print(f"Embedding used for FCM: {X_rel.shape}")


# ============================================================
# 8. STANDARDIZE EMBEDDING
# ============================================================

if STANDARDIZE_FEATURES:

    scaler = StandardScaler()

    X = scaler.fit_transform(X_rel)

    print("\nFeature standardization: ENABLED")

else:

    X = X_rel.copy()

    print("\nFeature standardization: DISABLED")


print("\nEmbedding statistics:")
print(f"Overall mean: {X.mean():.8f}")
print(f"Overall std : {X.std():.8f}")
print(f"Minimum     : {X.min():.8f}")
print(f"Maximum     : {X.max():.8f}")


# ============================================================
# 9. FCM INITIALIZATION
# ============================================================

def make_initial_membership(X_data, K, seed):
    """
    Create a non-uniform initial membership matrix using KMeans.

    This is important because random FCM initialization was
    producing an almost perfectly uniform solution.
    """

    rng = np.random.default_rng(seed)

    km = KMeans(
        n_clusters=K,
        random_state=seed,
        n_init=10
    )

    labels = km.fit_predict(X_data)

    centers = km.cluster_centers_

    # Squared distance from every point to every center.
    diff = X_data[:, None, :] - centers[None, :, :]
    dist2 = np.sum(diff ** 2, axis=2)

    dist2 += 1e-12

    # Initial fuzzy membership.
    exponent = 1.0 / (FUZZINESS_M - 1.0)

    inv_dist = dist2 ** (-exponent)

    U = inv_dist / inv_dist.sum(axis=1, keepdims=True)

    # Small random perturbation prevents exact symmetry.
    noise = rng.normal(
        loc=0.0,
        scale=1e-6,
        size=U.shape
    )

    U = U + noise

    U = np.clip(U, 1e-12, None)

    U /= U.sum(axis=1, keepdims=True)

    return U.T


# ============================================================
# 10. FCM HELPER
# ============================================================

def run_best_fcm(X_data, K):
    """
    Run FCM multiple times and keep the solution with
    the lowest final objective function.
    """

    best = None

    for restart in range(N_RESTARTS):

        seed = RANDOM_SEED + K * 1000 + restart

        U0 = make_initial_membership(
            X_data,
            K,
            seed
        )

        try:

            (
                centers,
                u,
                u0,
                d,
                jm,
                p,
                fpc
            ) = fuzz.cluster.cmeans(
                X_data.T,
                c=K,
                m=FUZZINESS_M,
                error=ERROR,
                maxiter=MAXITER,
                init=U0,
                seed=seed
            )

        except TypeError:

            # Compatibility with older scikit-fuzzy versions
            (
                centers,
                u,
                u0,
                d,
                jm,
                p,
                fpc
            ) = fuzz.cluster.cmeans(
                X_data.T,
                c=K,
                m=FUZZINESS_M,
                error=ERROR,
                maxiter=MAXITER,
                init=U0
            )

        final_objective = float(jm[-1])

        if best is None or final_objective < best["objective"]:

            best = {
                "centers": centers,
                "u": u,
                "fpc": float(fpc),
                "objective": final_objective,
                "iterations": len(jm),
            }

    return best


# ============================================================
# 11. FUZZY DIAGNOSTICS
# ============================================================

def membership_diagnostics(U):

    row_sums = U.sum(axis=1)

    uniform = np.ones_like(U) / U.shape[1]

    deviation_from_uniform = np.mean(
        np.abs(U - uniform)
    )

    membership_std = np.std(U)

    row_sum_error = np.max(
        np.abs(row_sums - 1.0)
    )

    return {
        "membership_min": U.min(),
        "membership_max": U.max(),
        "membership_mean": U.mean(),
        "membership_std": membership_std,
        "mean_abs_deviation_from_uniform":
            deviation_from_uniform,
        "max_row_sum_error":
            row_sum_error,
    }


def center_separation(centers):

    if len(centers) < 2:
        return np.nan

    distances = []

    for i in range(len(centers)):

        for j in range(i + 1, len(centers)):

            distances.append(
                np.linalg.norm(
                    centers[i] - centers[j]
                )
            )

    return float(np.mean(distances))


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


# ============================================================
# 12. CLUSTERING
# ============================================================

K_RANGE = range(MIN_K, (N // 3) + 1)

results = []
membership_results = {}
center_results = {}

print("\n" + "=" * 70)
print("FUZZY C-MEANS")
print("=" * 70)

for K in K_RANGE:

    print(f"\nRunning K={K} ...")

    best = run_best_fcm(X, K)

    centers = best["centers"]
    U = best["u"].T

    labels = np.argmax(U, axis=1)

    diag = membership_diagnostics(U)

    center_dist = center_separation(centers)
    fuzzy_sil = fuzzy_silhouette(D, U)

    unique_labels = np.unique(labels)

    # --------------------------------------------------------
    # Hard-label metrics
    # --------------------------------------------------------

    if len(unique_labels) >= 2:

        cosine_sil = silhouette_score(
            D,
            labels,
            metric="precomputed"
        )

        euclidean_sil = silhouette_score(
            X,
            labels,
            metric="euclidean"
        )

        db = davies_bouldin_score(
            X,
            labels
        )

        ch = calinski_harabasz_score(
            X,
            labels
        )

    else:

        cosine_sil = np.nan
        euclidean_sil = np.nan
        db = np.nan
        ch = np.nan

    # --------------------------------------------------------
    # FPC baseline
    # --------------------------------------------------------

    uniform_fpc = 1.0 / K

    fpc_excess = best["fpc"] - uniform_fpc

    results.append({

        "K": K,

        "fpc":
            best["fpc"],

        "uniform_fpc_baseline":
            uniform_fpc,

        "fpc_excess":
            fpc_excess,

        "membership_std":
            diag["membership_std"],

        "mean_abs_deviation_from_uniform":
            diag["mean_abs_deviation_from_uniform"],

        "membership_min":
            diag["membership_min"],

        "membership_max":
            diag["membership_max"],

        "row_sum_error":
            diag["max_row_sum_error"],

        "center_separation":
            center_dist,

        "fcm_objective":
            best["objective"],

        "iterations":
            best["iterations"],

        "cosine_silhouette":
            cosine_sil,

        "silhouette_score":
            cosine_sil,

        "fuzzy_silhouette":
            fuzzy_sil,

        "euclidean_silhouette":
            euclidean_sil,

        "davies_bouldin":
            db,

        "calinski_harabasz":
            ch,

    })

    membership_results[K] = U
    center_results[K] = centers

    print(
        f"  FPC                    = {best['fpc']:.8f}"
    )

    print(
        f"  Uniform FPC baseline   = {uniform_fpc:.8f}"
    )

    print(
        f"  FPC excess             = {fpc_excess:.8e}"
    )

    print(
        f"  Membership std         = "
        f"{diag['membership_std']:.8e}"
    )

    print(
        f"  Deviation from uniform = "
        f"{diag['mean_abs_deviation_from_uniform']:.8e}"
    )

    print(
        f"  Center separation      = "
        f"{center_dist:.8f}"
    )

    print(
        f"  Cosine silhouette      = "
        f"{cosine_sil:.6f}"
    )

    print(
        f"  Fuzzy silhouette       = "
        f"{fuzzy_sil:.6f}"
    )


# ============================================================
# 13. RESULTS TABLE
# ============================================================

results_df = pd.DataFrame(results)

results_df.to_csv(
    os.path.join(
        OUT_DIR,
        "clustering_results.csv"
    ),
    index=False
)

print("\n" + "=" * 70)
print("CLUSTERING SUMMARY")
print("=" * 70)

print(
    results_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}"
    )
)


# ============================================================
# 14. DETECT FCM DEGENERACY
# ============================================================

max_membership_deviation = (
    results_df[
        "mean_abs_deviation_from_uniform"
    ].max()
)

if max_membership_deviation < 0.01:

    print("\n" + "!" * 70)
    print("WARNING: FCM MEMBERSHIPS ARE NEARLY UNIFORM")
    print("!" * 70)

    print(
        "The fuzzy memberships are still extremely close "
        "to 1/K."
    )

    print(
        "This means the data do not currently provide "
        "strong fuzzy-C-means separation in this embedding."
    )

    print(
        "Do NOT interpret a tiny FPC difference as evidence "
        "for a meaningful fuzzy cluster structure."
    )

else:

    print("\nFCM memberships show non-trivial separation.")


# ============================================================
# 15. BEST K BY DIFFERENT METRICS
# ============================================================

print("\n" + "=" * 70)
print("BEST K BY METRIC")
print("=" * 70)

# FPC
k_fpc = int(
    results_df.loc[
        results_df["fpc"].idxmax(),
        "K"
    ]
)

print(
    f"Highest FPC             : K={k_fpc}"
)

# Fuzzy Silhouette
valid_fuzzy = results_df[results_df["fuzzy_silhouette"].notna()]
k_fuzzy = int(
    valid_fuzzy.loc[valid_fuzzy["fuzzy_silhouette"].idxmax(), "K"]
)
print(
    f"Highest Fuzzy silhouette : K={k_fuzzy}, "
    f"score={valid_fuzzy.loc[valid_fuzzy['K'] == k_fuzzy, 'fuzzy_silhouette'].iloc[0]:.6f}"
)

# Cosine silhouette
valid_cosine = results_df[
    results_df["cosine_silhouette"].notna()
]

if len(valid_cosine) > 0:

    k_cosine = int(
        valid_cosine.loc[
            valid_cosine[
                "cosine_silhouette"
            ].idxmax(),
            "K"
        ]
    )

    cosine_value = valid_cosine[
        valid_cosine["K"] == k_cosine
    ]["cosine_silhouette"].iloc[0]

    print(
        f"Highest cosine silhouette: "
        f"K={k_cosine}, "
        f"score={cosine_value:.6f}"
    )

else:

    k_cosine = MIN_K
    print("Cosine silhouette unavailable.")


# Euclidean silhouette
valid_euclidean = results_df[
    results_df["euclidean_silhouette"].notna()
]

if len(valid_euclidean) > 0:

    k_euclidean = int(
        valid_euclidean.loc[
            valid_euclidean[
                "euclidean_silhouette"
            ].idxmax(),
            "K"
        ]
    )

    euclidean_value = valid_euclidean[
        valid_euclidean["K"] == k_euclidean
    ]["euclidean_silhouette"].iloc[0]

    print(
        f"Highest Euclidean silhouette: "
        f"K={k_euclidean}, "
        f"score={euclidean_value:.6f}"
    )


# DB
valid_db = results_df[
    results_df["davies_bouldin"].notna()
]

if len(valid_db) > 0:

    k_db = int(
        valid_db.loc[
            valid_db["davies_bouldin"].idxmin(),
            "K"
        ]
    )

    db_value = valid_db[
        valid_db["K"] == k_db
    ]["davies_bouldin"].iloc[0]

    print(
        f"Lowest Davies-Bouldin    : "
        f"K={k_db}, "
        f"score={db_value:.6f}"
    )


# CH
valid_ch = results_df[
    results_df["calinski_harabasz"].notna()
]

if len(valid_ch) > 0:

    k_ch = int(
        valid_ch.loc[
            valid_ch["calinski_harabasz"].idxmax(),
            "K"
        ]
    )

    ch_value = valid_ch[
        valid_ch["K"] == k_ch
    ]["calinski_harabasz"].iloc[0]

    print(
        f"Highest Calinski-Harabasz: "
        f"K={k_ch}, "
        f"score={ch_value:.6f}"
    )


# ============================================================
# 16. PRIMARY K
# ============================================================

# Primary selection uses the membership-weighted Fuzzy Silhouette.
#
# IMPORTANT:
# This does NOT mean the resulting K is automatically
# scientifically meaningful. The silhouette must still be
# interpreted together with membership strength and stability.

best_k = k_fuzzy

print("\n" + "=" * 70)
print(f"PRIMARY K = {best_k}")
print("=" * 70)

print(
    "Primary selection criterion: "
    "highest Fuzzy Silhouette."
)


# ============================================================
# 17. SAVE FUZZY MEMBERSHIP MATRIX
# ============================================================

U_best = membership_results[best_k]

membership_df = pd.DataFrame(
    U_best,
    index=ids,
    columns=[
        f"Cluster_{k + 1}"
        for k in range(best_k)
    ]
)

membership_path = os.path.join(
    OUT_DIR,
    f"fuzzy_membership_K{best_k}.csv"
)

membership_df.to_csv(
    membership_path
)
membership_df.to_csv(
    os.path.join(OUT_DIR, "fuzzy_membership_matrix.csv")
)

print(
    f"\nSaved fuzzy membership matrix:\n"
    f"{membership_path}"
)


# ============================================================
# 18. SAVE HARD LABELS
# ============================================================

hard_labels_df = pd.DataFrame(
    {
        "ID": ids,
        "Cluster": np.argmax(
            U_best,
            axis=1
        ) + 1,
        "Max_Membership":
            np.max(U_best, axis=1)
    }
)

hard_labels_path = os.path.join(
    OUT_DIR,
    f"hard_labels_K{best_k}.csv"
)

hard_labels_df.to_csv(
    hard_labels_path,
    index=False
)

print(
    f"Saved hard labels:\n"
    f"{hard_labels_path}"
)


# ============================================================
# 19. THRESHOLDED FUZZY OVERLAP
# ============================================================

print("\n" + "=" * 70)
print("THRESHOLDED FUZZY OVERLAP")
print("=" * 70)

overlap_results = []
U_best = membership_results[best_k]

for threshold in OVERLAP_THRESHOLDS:
    U_overlap = (U_best >= threshold).astype(int)
    valid_clusters = np.where(U_overlap.sum(axis=0) >= 2)[0]
    U_overlap = U_overlap[:, valid_clusters]
    membership_count = U_overlap.sum(axis=1)
    overlap_results.append({
        "threshold": threshold,
        "K": best_k,
        "actual_clusters": U_overlap.shape[1],
        "overlap_ratio": np.mean(membership_count > 1),
        "average_cluster_memberships": np.mean(membership_count),
        "max_cluster_memberships": np.max(membership_count),
    })

    threshold_label = f"{threshold:.2f}".replace(".", "_")
    pd.DataFrame(
        U_overlap,
        index=ids,
        columns=[f"Cluster_{index + 1}" for index in valid_clusters],
    ).to_csv(
        os.path.join(
            OUT_DIR,
            f"overlapping_membership_threshold_{threshold_label}_K{best_k}.csv",
        )
    )

    assignments = []
    for cluster_index, source_cluster in enumerate(valid_clusters):
        for item_index in np.where(U_best[:, source_cluster] >= threshold)[0]:
            assignments.append({
                "threshold": threshold,
                "K": best_k,
                "cluster": f"Cluster_{cluster_index + 1}",
                "intelligence_id": ids[item_index],
                "membership": float(U_best[item_index, source_cluster]),
            })

    pd.DataFrame(assignments).to_csv(
        os.path.join(
            OUT_DIR,
            f"cluster_assignments_threshold_{threshold_label}_K{best_k}.csv",
        ),
        index=False,
    )


overlap_results_df = pd.DataFrame(
    overlap_results
)

overlap_results_df.to_csv(
    os.path.join(
        OUT_DIR,
        "overlap_results.csv"
    ),
    index=False
)

print(
    overlap_results_df.to_string(
        index=False
    )
)


# ============================================================
# 21. MEMBERSHIP DIAGNOSTIC FOR PRIMARY K
# ============================================================

print("\n" + "=" * 70)
print(f"PRIMARY K={best_k} MEMBERSHIP DIAGNOSTICS")
print("=" * 70)

U = membership_results[best_k]

print(
    f"Membership min        : {U.min():.8f}"
)

print(
    f"Membership max        : {U.max():.8f}"
)

print(
    f"Membership mean       : {U.mean():.8f}"
)

print(
    f"Membership std        : {U.std():.8f}"
)

print(
    f"Row-sum min           : "
    f"{U.sum(axis=1).min():.8f}"
)

print(
    f"Row-sum max           : "
    f"{U.sum(axis=1).max():.8f}"
)

print(
    "\nFirst 10 membership rows:"
)

print(
    pd.DataFrame(
        U[:10],
        index=ids[:10],
        columns=[
            f"Cluster_{k + 1}"
            for k in range(best_k)
        ]
    ).to_string()
)


# ============================================================
# 22. PLOTS
# ============================================================

plot_metrics = {

    "fpc":
        "Fuzzy Partition Coefficient",

    "fpc_excess":
        "FPC Excess Above Uniform Baseline",

    "cosine_silhouette":
        "Cosine-Distance Silhouette",

    "fuzzy_silhouette":
        "Fuzzy Silhouette",

    "silhouette_score":
        "Silhouette Score",

    "euclidean_silhouette":
        "Euclidean Silhouette",

    "davies_bouldin":
        "Davies-Bouldin Index",

    "calinski_harabasz":
        "Calinski-Harabasz Index",

    "membership_std":
        "Membership Standard Deviation",

    "center_separation":
        "Mean Center Separation",

}


for metric, title in plot_metrics.items():

    plt.figure(
        figsize=(8, 5)
    )

    plt.plot(
        results_df["K"],
        results_df[metric],
        marker="o"
    )

    plt.axvline(
        best_k,
        linestyle="--",
        label=f"Primary K = {best_k}"
    )

    plt.xlabel(
        "Number of Clusters (K)"
    )

    plt.ylabel(
        metric
    )

    plt.title(
        title
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUT_DIR,
            f"{metric}_vs_K.png"
        ),
        dpi=300
    )

    plt.close()


# ============================================================
# 23. MEMBERSHIP HEATMAP
# ============================================================

plt.figure(
    figsize=(10, 8)
)

plt.imshow(
    U_best,
    aspect="auto",
    interpolation="nearest"
)

plt.colorbar(
    label="Membership"
)

plt.xlabel(
    "Cluster"
)

plt.ylabel(
    "Intelligence Item"
)

plt.title(
    f"Fuzzy Membership Matrix — K={best_k}"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        f"membership_heatmap_K{best_k}.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 24. SAVE EMBEDDING
# ============================================================

embedding_df = pd.DataFrame(
    X,
    index=ids,
    columns=[
        f"Dimension_{i + 1}"
        for i in range(X.shape[1])
    ]
)

embedding_df.to_csv(
    os.path.join(
        OUT_DIR,
        "spectral_embedding.csv"
    )
)


# ============================================================
# 25. SAVE CLEAN MATRICES
# ============================================================

pd.DataFrame(
    S,
    index=ids,
    columns=ids
).to_csv(
    os.path.join(
        OUT_DIR,
        "clean_similarity_matrix.csv"
    )
)

pd.DataFrame(
    D,
    index=ids,
    columns=ids
).to_csv(
    os.path.join(
        OUT_DIR,
        "cosine_distance_matrix.csv"
    )
)


# ============================================================
# 26. FINAL INTERPRETATION CHECK
# ============================================================

print("\n" + "=" * 70)
print("FINAL CHECK")
print("=" * 70)

primary_row = results_df[
    results_df["K"] == best_k
].iloc[0]

print(
    f"Primary K                  : {best_k}"
)

print(
    f"Cosine silhouette          : "
    f"{primary_row['cosine_silhouette']:.6f}"
)

print(
    f"FPC                        : "
    f"{primary_row['fpc']:.8f}"
)

print(
    f"Uniform FPC baseline       : "
    f"{primary_row['uniform_fpc_baseline']:.8f}"
)

print(
    f"FPC excess                 : "
    f"{primary_row['fpc_excess']:.8e}"
)

print(
    f"Membership std             : "
    f"{primary_row['membership_std']:.8e}"
)

print(
    f"Center separation          : "
    f"{primary_row['center_separation']:.8f}"
)

print(
    f"Mean deviation from uniform:"
    f" {primary_row['mean_abs_deviation_from_uniform']:.8e}"
)

if (
    primary_row["fpc_excess"] < 0.001
    and
    primary_row["membership_std"] < 0.01
):

    print("\nRESULT:")
    print(
        "FCM remains essentially uniform."
    )

    print(
        "The data do not currently support "
        "a strong fuzzy-C-means partition."
    )

elif primary_row["cosine_silhouette"] < 0.20:

    print("\nRESULT:")
    print(
        "Some geometric separation exists, "
        "but it is weak."
    )

else:

    print("\nRESULT:")
    print(
        "Non-trivial cluster separation "
        "is present in the current representation."
    )


print("\nAll results saved to:")
print(OUT_DIR)

print("\nDone.")

ANALYZER_PATH = os.path.join(
    BASE_DIR,
    "archive",
    "analyze_cluster_insights.py",
)
if os.path.exists(ANALYZER_PATH):
    print("\nRunning cluster insight analysis with Ollama...")
    subprocess.run([sys.executable, ANALYZER_PATH], check=True)