import os
import glob
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.manifold import MDS
from sklearn.metrics import silhouette_score, davies_bouldin_score

import skfuzzy as fuzz

warnings.filterwarnings("ignore")


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"

OUT_DIR = os.path.join(
    BASE_DIR,
    "results",
    "result_cosine_baseline_corrected"
)

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# 2. LOAD COSINE SIMILARITY MATRIX
# ============================================================

CSV_FILE = os.path.join(
    BASE_DIR,
    "similarity_results",
    "cosine_experiment",
    "similarity_matrix.csv"
)

if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(
        f"Similarity matrix was not found:\n{CSV_FILE}"
    )

print("=" * 70)
print("USING SIMILARITY MATRIX")
print("=" * 70)
print(CSV_FILE)


# ============================================================
# 3. READ MATRIX
# ============================================================

df = pd.read_csv(CSV_FILE, index_col=0)

ids = df.index.astype(str).tolist()

S = df.values.astype(float)

if S.shape[0] != S.shape[1]:
    raise ValueError(
        f"Similarity matrix must be square. Found shape: {S.shape}"
    )

N = S.shape[0]

print(f"\nNumber of intelligence items: {N}")


# ============================================================
# 4. CLEAN AND VALIDATE SIMILARITY MATRIX
# ============================================================

S = np.nan_to_num(
    S,
    nan=0.0,
    posinf=1.0,
    neginf=-1.0
)

# Force symmetry
S = (S + S.T) / 2.0

# Cosine similarity is theoretically [-1, 1]
S = np.clip(S, -1.0, 1.0)

# Self-similarity
np.fill_diagonal(S, 1.0)


# ============================================================
# 5. SIMILARITY DIAGNOSTICS
# ============================================================

off_diag_mask = ~np.eye(N, dtype=bool)
off_diag = S[off_diag_mask]

print("\n" + "=" * 70)
print("SIMILARITY MATRIX DIAGNOSTICS")
print("=" * 70)

print(f"Minimum similarity : {off_diag.min():.8f}")
print(f"Maximum similarity : {off_diag.max():.8f}")
print(f"Mean similarity    : {off_diag.mean():.8f}")
print(f"Median similarity  : {np.median(off_diag):.8f}")
print(f"Std similarity     : {off_diag.std():.8f}")

print("\nSimilarity percentiles:")

for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(
        f"{p:>2}% : "
        f"{np.percentile(off_diag, p):.8f}"
    )


# ============================================================
# 6. CONVERT COSINE SIMILARITY -> COSINE DISTANCE
# ============================================================

# Cosine distance:
#
#     D(i,j) = 1 - cosine_similarity(i,j)
#
# Range is [0, 2].

D = 1.0 - S

D = np.clip(D, 0.0, 2.0)

np.fill_diagonal(D, 0.0)


print("\n" + "=" * 70)
print("DISTANCE MATRIX DIAGNOSTICS")
print("=" * 70)

print(f"Minimum distance : {D[off_diag_mask].min():.8f}")
print(f"Maximum distance : {D[off_diag_mask].max():.8f}")
print(f"Mean distance    : {D[off_diag_mask].mean():.8f}")
print(f"Median distance  : {np.median(D[off_diag_mask]):.8f}")
print(f"Std distance     : {D[off_diag_mask].std():.8f}")


# ============================================================
# 7. MDS REPRESENTATION
# ============================================================

print("\n" + "=" * 70)
print("MDS")
print("=" * 70)

MDS_DIMENSION = 10

mds = MDS(
    n_components=MDS_DIMENSION,
    dissimilarity="precomputed",
    random_state=42,
    normalized_stress="auto",
    n_init=4,
    max_iter=1000
)

X = mds.fit_transform(D)

print(f"MDS representation shape: {X.shape}")
print(f"MDS stress: {mds.stress_:.8f}")


# ============================================================
# 8. CHECK DIFFERENT MDS DIMENSIONS
# ============================================================

print("\n" + "=" * 70)
print("MDS DIMENSION DIAGNOSTIC")
print("=" * 70)

mds_dimension_results = []

for dim in [2, 5, 10, 15, 20]:

    if dim >= N:
        continue

    diagnostic_mds = MDS(
        n_components=dim,
        dissimilarity="precomputed",
        random_state=42,
        normalized_stress="auto",
        n_init=2,
        max_iter=1000
    )

    diagnostic_X = diagnostic_mds.fit_transform(D)

    stress = diagnostic_mds.stress_

    mds_dimension_results.append(
        {
            "dimension": dim,
            "stress": stress
        }
    )

    print(
        f"Dimensions = {dim:>2} | "
        f"Stress = {stress:.8f}"
    )

mds_dimension_df = pd.DataFrame(mds_dimension_results)

mds_dimension_df.to_csv(
    os.path.join(
        OUT_DIR,
        "mds_dimension_diagnostics.csv"
    ),
    index=False
)


# ============================================================
# 9. FUZZY SILHOUETTE
# ============================================================

def fuzzy_silhouette(
    X,
    membership
):
    """
    Membership-weighted fuzzy silhouette.

    Higher values indicate better cluster separation.

    Note:
    - The dominant cluster is determined using argmax membership.
    - Distances are weighted by fuzzy memberships.
    """

    N = X.shape[0]
    K = membership.shape[1]

    distances = np.linalg.norm(
        X[:, None, :] - X[None, :, :],
        axis=2
    )

    scores = []

    for i in range(N):

        own_cluster = np.argmax(
            membership[i]
        )

        own_weights = membership[
            :,
            own_cluster
        ].copy()

        own_weights[i] = 0.0

        if own_weights.sum() > 0:

            a_i = np.average(
                distances[i],
                weights=own_weights
            )

        else:

            a_i = 0.0

        other_cluster_distances = []

        for k in range(K):

            if k == own_cluster:
                continue

            weights = membership[:, k].copy()

            weights[i] = 0.0

            if weights.sum() > 0:

                distance_k = np.average(
                    distances[i],
                    weights=weights
                )

                other_cluster_distances.append(
                    distance_k
                )

        if not other_cluster_distances:
            continue

        b_i = min(
            other_cluster_distances
        )

        denominator = max(
            a_i,
            b_i
        )

        if denominator > 0:

            s_i = (
                b_i - a_i
            ) / denominator

            scores.append(s_i)

    if not scores:
        return np.nan

    return float(
        np.mean(scores)
    )


# ============================================================
# 10. XIE-BENI INDEX
# ============================================================

def xie_beni_index(
    X,
    membership,
    centers,
    m=2.0
):
    """
    Xie-Beni validity index.

    Lower values are better.
    """

    N = X.shape[0]
    K = centers.shape[0]

    numerator = 0.0

    for k in range(K):

        distances = (
            np.linalg.norm(
                X - centers[k],
                axis=1
            ) ** 2
        )

        numerator += np.sum(
            (membership[:, k] ** m)
            * distances
        )

    center_distances = []

    for k in range(K):

        for j in range(k + 1, K):

            d = (
                np.linalg.norm(
                    centers[k] - centers[j]
                ) ** 2
            )

            center_distances.append(d)

    if not center_distances:
        return np.inf

    min_center_distance = min(
        center_distances
    )

    if min_center_distance <= 1e-12:
        return np.inf

    return float(
        numerator
        /
        (
            N
            * min_center_distance
        )
    )


# ============================================================
# 11. KWON INDEX
# ============================================================

def kwon_index(
    X,
    membership,
    centers,
    m=2.0
):
    """
    Kwon fuzzy clustering validity index.

    Lower values are better.
    """

    N = X.shape[0]
    K = centers.shape[0]

    global_center = np.mean(
        X,
        axis=0
    )

    compactness = 0.0

    for k in range(K):

        distances = (
            np.linalg.norm(
                X - centers[k],
                axis=1
            ) ** 2
        )

        compactness += np.sum(
            (membership[:, k] ** m)
            * distances
        )

    center_dispersion = (
        np.sum(
            np.linalg.norm(
                centers - global_center,
                axis=1
            ) ** 2
        )
        / K
    )

    center_distances = []

    for k in range(K):

        for j in range(k + 1, K):

            d = (
                np.linalg.norm(
                    centers[k] - centers[j]
                ) ** 2
            )

            center_distances.append(d)

    if not center_distances:
        return np.inf

    min_center_distance = min(
        center_distances
    )

    if min_center_distance <= 1e-12:
        return np.inf

    return float(
        (
            compactness
            + center_dispersion
        )
        /
        min_center_distance
    )


# ============================================================
# 12. RUN FUZZY C-MEANS
# ============================================================

print("\n" + "=" * 70)
print("FUZZY C-MEANS")
print("=" * 70)

results = []

membership_results = {}

centers_results = {}

# Initial range kept moderate for interpretability.
# Can be expanded later if needed.
MAX_K = min(
    15,
    N - 1
)

for K in range(2, MAX_K + 1):

    print(
        f"\nRunning K = {K}"
    )

    centers, membership, _, _, _, _, fpc = (
        fuzz.cluster.cmeans(
            X.T,
            c=K,
            m=2.0,
            error=0.005,
            maxiter=1000,
            init=None,
            seed=42
        )
    )

    # skfuzzy returns:
    #
    # membership = K x N
    #
    # Convert to:
    #
    # U = N x K

    U = membership.T

    # --------------------------------------------------------
    # Membership diagnostics
    # --------------------------------------------------------

    row_sums = U.sum(axis=1)

    membership_deviation = np.max(
        np.abs(
            row_sums - 1.0
        )
    )

    membership_min = U.min()
    membership_max = U.max()
    membership_mean = U.mean()

    uniform_baseline = 1.0 / K

    fpc_expected_uniform = (
        1.0 / K
    )

    fpc_excess_over_uniform = (
        fpc - fpc_expected_uniform
    )

    # --------------------------------------------------------
    # Fuzzy silhouette
    # --------------------------------------------------------

    fs = fuzzy_silhouette(
        X,
        U
    )

    # --------------------------------------------------------
    # Xie-Beni
    # --------------------------------------------------------

    xb = xie_beni_index(
        X,
        U,
        centers
    )

    # --------------------------------------------------------
    # Kwon
    # --------------------------------------------------------

    kwon = kwon_index(
        X,
        U,
        centers
    )

    # --------------------------------------------------------
    # Hard labels
    # --------------------------------------------------------

    labels = np.argmax(
        U,
        axis=1
    )

    unique_labels = np.unique(
        labels
    )

    # --------------------------------------------------------
    # Ordinary silhouette in MDS Euclidean space
    # --------------------------------------------------------

    if len(unique_labels) > 1:

        ordinary_silhouette_mds = (
            silhouette_score(
                X,
                labels
            )
        )

        db = (
            davies_bouldin_score(
                X,
                labels
            )
        )

        # ----------------------------------------------------
        # Silhouette directly on original cosine distance
        # ----------------------------------------------------

        ordinary_silhouette_cosine = (
            silhouette_score(
                D,
                labels,
                metric="precomputed"
            )
        )

    else:

        ordinary_silhouette_mds = np.nan
        ordinary_silhouette_cosine = np.nan
        db = np.nan

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    results.append(
        {
            "K": K,

            "fpc": fpc,

            "fpc_uniform_baseline":
                fpc_expected_uniform,

            "fpc_excess_over_uniform":
                fpc_excess_over_uniform,

            "membership_min":
                membership_min,

            "membership_max":
                membership_max,

            "membership_mean":
                membership_mean,

            "membership_row_sum_max_deviation":
                membership_deviation,

            "fuzzy_silhouette":
                fs,

            "ordinary_silhouette_mds":
                ordinary_silhouette_mds,

            "ordinary_silhouette_cosine":
                ordinary_silhouette_cosine,

            "davies_bouldin":
                db,

            "xie_beni":
                xb,

            "kwon_index":
                kwon
        }
    )

    membership_results[K] = U
    centers_results[K] = centers

    # --------------------------------------------------------
    # Print diagnostics
    # --------------------------------------------------------

    print(
        f"FPC                         : {fpc:.8f}"
    )

    print(
        f"Uniform FPC baseline       : "
        f"{fpc_expected_uniform:.8f}"
    )

    print(
        f"FPC excess over baseline   : "
        f"{fpc_excess_over_uniform:.8f}"
    )

    print(
        f"Membership min             : "
        f"{membership_min:.8f}"
    )

    print(
        f"Membership max             : "
        f"{membership_max:.8f}"
    )

    print(
        f"Membership row-sum error   : "
        f"{membership_deviation:.8e}"
    )

    print(
        f"Fuzzy silhouette           : "
        f"{fs:.8f}"
    )

    print(
        f"Silhouette MDS             : "
        f"{ordinary_silhouette_mds:.8f}"
    )

    print(
        f"Silhouette cosine distance: "
        f"{ordinary_silhouette_cosine:.8f}"
    )

    print(
        f"Davies-Bouldin             : "
        f"{db:.8f}"
    )

    print(
        f"Xie-Beni                   : "
        f"{xb:.8f}"
    )

    print(
        f"Kwon                       : "
        f"{kwon:.8f}"
    )

    if K == 2:

        print(
            "\nFirst 10 membership rows for K=2:"
        )

        print(
            U[:10]
        )


# ============================================================
# 13. SAVE RESULTS
# ============================================================

results_df = pd.DataFrame(
    results
)

results_file = os.path.join(
    OUT_DIR,
    "clustering_metrics.csv"
)

results_df.to_csv(
    results_file,
    index=False
)


# ============================================================
# 14. PRINT COMPLETE RESULTS
# ============================================================

print("\n" + "=" * 70)
print("CLUSTERING SUMMARY")
print("=" * 70)

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# 15. BEST K BY METRIC
# ============================================================

best_k_by_metric = {}

# Higher is better
best_k_by_metric[
    "fpc"
] = int(
    results_df.loc[
        results_df["fpc"].idxmax(),
        "K"
    ]
)

best_k_by_metric[
    "fuzzy_silhouette"
] = int(
    results_df.loc[
        results_df["fuzzy_silhouette"].idxmax(),
        "K"
    ]
)

best_k_by_metric[
    "ordinary_silhouette_mds"
] = int(
    results_df.loc[
        results_df[
            "ordinary_silhouette_mds"
        ].idxmax(),
        "K"
    ]
)

best_k_by_metric[
    "ordinary_silhouette_cosine"
] = int(
    results_df.loc[
        results_df[
            "ordinary_silhouette_cosine"
        ].idxmax(),
        "K"
    ]
)

# Lower is better
best_k_by_metric[
    "davies_bouldin"
] = int(
    results_df.loc[
        results_df["davies_bouldin"].idxmin(),
        "K"
    ]
)

best_k_by_metric[
    "xie_beni"
] = int(
    results_df.loc[
        results_df["xie_beni"].idxmin(),
        "K"
    ]
)

best_k_by_metric[
    "kwon_index"
] = int(
    results_df.loc[
        results_df["kwon_index"].idxmin(),
        "K"
    ]
)


print("\n" + "=" * 70)
print("BEST K BY METRIC")
print("=" * 70)

for metric, best_k in best_k_by_metric.items():

    value = results_df.loc[
        results_df["K"] == best_k,
        metric
    ].iloc[0]

    print(
        f"{metric:35s} "
        f"K={best_k:<3d} "
        f"score={value:.8f}"
    )


# ============================================================
# 16. SAVE BEST-K SUMMARY
# ============================================================

best_k_summary = []

for metric, best_k in best_k_by_metric.items():

    value = results_df.loc[
        results_df["K"] == best_k,
        metric
    ].iloc[0]

    best_k_summary.append(
        {
            "metric": metric,
            "best_K": best_k,
            "score": value
        }
    )

best_k_df = pd.DataFrame(
    best_k_summary
)

best_k_df.to_csv(
    os.path.join(
        OUT_DIR,
        "best_k_by_metric.csv"
    ),
    index=False
)


# ============================================================
# 17. SELECT PRIMARY K
# ============================================================

# Primary selection based on fuzzy silhouette.
#
# This is intentionally kept separate from the other
# diagnostic metrics.

BEST_K = best_k_by_metric[
    "fuzzy_silhouette"
]

print("\n" + "=" * 70)
print("SELECTED PRIMARY K")
print("=" * 70)

print(
    f"Primary metric : fuzzy_silhouette"
)

print(
    f"Selected K     : {BEST_K}"
)


# ============================================================
# 18. SAVE BEST MEMBERSHIP MATRIX
# ============================================================

U_best = membership_results[
    BEST_K
]

membership_df = pd.DataFrame(
    U_best,
    index=ids,
    columns=[
        f"Cluster_{k + 1}"
        for k in range(BEST_K)
    ]
)

membership_file = os.path.join(
    OUT_DIR,
    "fuzzy_membership_matrix.csv"
)

membership_df.to_csv(
    membership_file
)


# ============================================================
# 19. SAVE HARD CLUSTER ASSIGNMENTS
# ============================================================

hard_labels = np.argmax(
    U_best,
    axis=1
)

hard_assignment_df = pd.DataFrame(
    {
        "intelligence_id": ids,
        "cluster": hard_labels + 1,
        "max_membership": U_best.max(axis=1)
    }
)

hard_assignment_file = os.path.join(
    OUT_DIR,
    "hard_cluster_assignments.csv"
)

hard_assignment_df.to_csv(
    hard_assignment_file,
    index=False
)


# ============================================================
# 20. BEST-K MEMBERSHIP DIAGNOSTICS
# ============================================================

print("\n" + "=" * 70)
print("BEST-K MEMBERSHIP DIAGNOSTICS")
print("=" * 70)

print(
    f"BEST_K = {BEST_K}"
)

print(
    f"Membership minimum : "
    f"{U_best.min():.8f}"
)

print(
    f"Membership maximum : "
    f"{U_best.max():.8f}"
)

print(
    f"Membership mean    : "
    f"{U_best.mean():.8f}"
)

print(
    f"Row sum minimum    : "
    f"{U_best.sum(axis=1).min():.8f}"
)

print(
    f"Row sum maximum    : "
    f"{U_best.sum(axis=1).max():.8f}"
)

print(
    f"FPC                : "
    f"{results_df.loc[results_df['K'] == BEST_K, 'fpc'].iloc[0]:.8f}"
)

print("\nFirst 10 membership rows:")

print(
    membership_df.head(10).to_string()
)


# ============================================================
# 21. PLOT FPC
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df["fpc"],
    marker="o",
    label="FPC"
)

plt.plot(
    results_df["K"],
    results_df[
        "fpc_uniform_baseline"
    ],
    linestyle="--",
    label="Uniform baseline (1/K)"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Fuzzy Partition Coefficient"
)

plt.title(
    "FPC vs. Number of Clusters"
)

plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "fpc_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 22. PLOT FPC EXCESS OVER UNIFORM BASELINE
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df[
        "fpc_excess_over_uniform"
    ],
    marker="o"
)

plt.axhline(
    0,
    linestyle="--"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "FPC - 1/K"
)

plt.title(
    "FPC Excess Over Uniform Membership Baseline"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "fpc_excess_over_uniform_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 23. PLOT FUZZY SILHOUETTE
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df["fuzzy_silhouette"],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Fuzzy Silhouette Score"
)

plt.title(
    "Fuzzy Silhouette vs. Number of Clusters"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "fuzzy_silhouette_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 24. PLOT ORDINARY SILHOUETTE - MDS
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df[
        "ordinary_silhouette_mds"
    ],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Silhouette Score"
)

plt.title(
    "Silhouette in MDS Space vs. Number of Clusters"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "silhouette_mds_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 25. PLOT ORDINARY SILHOUETTE - ORIGINAL COSINE DISTANCE
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df[
        "ordinary_silhouette_cosine"
    ],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Silhouette Score"
)

plt.title(
    "Silhouette Using Original Cosine Distance"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "silhouette_cosine_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 26. PLOT DAVIES-BOULDIN
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df["davies_bouldin"],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Davies-Bouldin Index"
)

plt.title(
    "Davies-Bouldin Index vs. Number of Clusters"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "davies_bouldin_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 27. PLOT XIE-BENI
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df["xie_beni"],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Xie-Beni Index"
)

plt.title(
    "Xie-Beni Index vs. Number of Clusters"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "xie_beni_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 28. PLOT KWON
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    results_df["K"],
    results_df["kwon_index"],
    marker="o"
)

plt.xlabel(
    "Number of Clusters (K)"
)

plt.ylabel(
    "Kwon Index"
)

plt.title(
    "Kwon Index vs. Number of Clusters"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "kwon_index_vs_K.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 29. PLOT MDS STRESS
# ============================================================

plt.figure(
    figsize=(8, 5)
)

plt.plot(
    mds_dimension_df["dimension"],
    mds_dimension_df["stress"],
    marker="o"
)

plt.xlabel(
    "MDS Dimensions"
)

plt.ylabel(
    "MDS Stress"
)

plt.title(
    "MDS Stress vs. Number of Dimensions"
)

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        OUT_DIR,
        "mds_stress_vs_dimensions.png"
    ),
    dpi=300
)

plt.close()


# ============================================================
# 30. SAVE CLEANED MATRICES
# ============================================================

S_df = pd.DataFrame(
    S,
    index=ids,
    columns=ids
)

S_df.to_csv(
    os.path.join(
        OUT_DIR,
        "cleaned_cosine_similarity_matrix.csv"
    )
)

D_df = pd.DataFrame(
    D,
    index=ids,
    columns=ids
)

D_df.to_csv(
    os.path.join(
        OUT_DIR,
        "cosine_distance_matrix.csv"
    )
)


# ============================================================
# 31. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print(
    f"Output directory:\n{OUT_DIR}"
)

print(
    f"\nClustering metrics:\n{results_file}"
)

print(
    f"\nMembership matrix:\n{membership_file}"
)

print(
    f"\nHard assignments:\n{hard_assignment_file}"
)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)