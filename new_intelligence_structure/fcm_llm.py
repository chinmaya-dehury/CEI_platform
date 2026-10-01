import os
import subprocess
import sys
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import skfuzzy as fuzz
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.manifold import MDS
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"
OUT_DIR = os.path.join(BASE_DIR, "results", "result_llm_fcm")
CSV_FILE = os.path.join(BASE_DIR, "similarity_results", "llm_experiment", "llm_similarity_matrix.csv")
MIN_CLUSTER_K = 8
FUZZINESS_M = 1.25
SIMILARITY_POWER = 3.0
N_RESTARTS = 20
RANDOM_SEED = 42
OVERLAP_THRESHOLDS = [0.40]
os.makedirs(OUT_DIR, exist_ok=True)


def fuzzy_silhouette(distance_matrix, membership):
    scores = []
    for item_index in range(distance_matrix.shape[0]):
        own_cluster = int(np.argmax(membership[item_index]))
        own_weights = membership[:, own_cluster].copy()
        own_weights[item_index] = 0.0
        own_distance = np.average(distance_matrix[item_index], weights=own_weights)
        other_distances = []
        for cluster_index in range(membership.shape[1]):
            if cluster_index == own_cluster:
                continue
            weights = membership[:, cluster_index].copy()
            weights[item_index] = 0.0
            if weights.sum() > 0:
                other_distances.append(np.average(distance_matrix[item_index], weights=weights))
        if other_distances:
            nearest_other = min(other_distances)
            denominator = max(own_distance, nearest_other)
            if denominator > 0:
                scores.append((nearest_other - own_distance) / denominator)
    return float(np.mean(scores)) if scores else np.nan


def initial_membership(features, cluster_count, seed):
    kmeans = KMeans(n_clusters=cluster_count, random_state=seed, n_init=10)
    kmeans.fit(features)
    distances = np.sum(
        (features[:, None, :] - kmeans.cluster_centers_[None, :, :]) ** 2,
        axis=2,
    ) + 1e-12
    membership = distances ** (-1.0 / (FUZZINESS_M - 1.0))
    membership /= membership.sum(axis=1, keepdims=True)
    noise = np.random.default_rng(seed).normal(0.0, 1e-6, membership.shape)
    membership = np.clip(membership + noise, 1e-12, None)
    return (membership / membership.sum(axis=1, keepdims=True)).T


def run_best_fcm(features, cluster_count):
    best = None
    for restart in range(N_RESTARTS):
        seed = RANDOM_SEED + cluster_count * 1000 + restart
        result = fuzz.cluster.cmeans(
            features.T,
            c=cluster_count,
            m=FUZZINESS_M,
            error=1e-6,
            maxiter=2000,
            init=initial_membership(features, cluster_count, seed),
        )
        objective = float(result[4][-1])
        if best is None or objective < best["objective"]:
            best = {
                "membership": result[1],
                "fpc": float(result[6]),
                "objective": objective,
            }
    return best


def evaluate_thresholds(distance, embedding, membership_results):
    metric_directions = {
        "fpc": "max",
        "fuzzy_silhouette": "max",
        "silhouette": "max",
        "davies_bouldin": "min",
        "calinski_harabasz": "max",
    }
    rows = []
    for threshold in OVERLAP_THRESHOLDS:
        for cluster_count, membership in membership_results.items():
            valid_clusters = np.where((membership >= threshold).sum(axis=0) >= 1)[0]
            selected_items = membership[:, valid_clusters].max(axis=1) >= threshold if len(valid_clusters) else np.zeros(len(membership), dtype=bool)
            if selected_items.sum() < 3 or len(valid_clusters) < 2:
                continue
            threshold_membership = membership[selected_items][:, valid_clusters]
            threshold_membership /= threshold_membership.sum(axis=1, keepdims=True)
            labels = np.argmax(threshold_membership, axis=1)
            actual_clusters = len(np.unique(labels))
            row = {
                "threshold": threshold,
                "K": cluster_count,
                "actual_clusters": actual_clusters,
                "threshold_items": int((membership.max(axis=1) >= threshold).sum()),
                "fpc": float(np.mean(np.sum(threshold_membership ** 2, axis=1))),
                "fuzzy_silhouette": fuzzy_silhouette(distance[np.ix_(selected_items, selected_items)], threshold_membership),
                "silhouette": np.nan,
                "davies_bouldin": np.nan,
                "calinski_harabasz": np.nan,
            }
            if 1 < len(np.unique(labels)) < selected_items.sum():
                row["silhouette"] = silhouette_score(distance[np.ix_(selected_items, selected_items)], labels, metric="precomputed")
                row["davies_bouldin"] = davies_bouldin_score(embedding[selected_items], labels)
                row["calinski_harabasz"] = calinski_harabasz_score(embedding[selected_items], labels)
            rows.append(row)

    metrics = pd.DataFrame(rows)
    candidate_metrics = metrics[metrics["K"] >= MIN_CLUSTER_K]
    selections = []
    for threshold in OVERLAP_THRESHOLDS:
        threshold_metrics = candidate_metrics[candidate_metrics["threshold"] == threshold]
        for metric, direction in metric_directions.items():
            valid = threshold_metrics.dropna(subset=[metric])
            if valid.empty:
                continue
            index = valid[metric].idxmax() if direction == "max" else valid[metric].idxmin()
            selected = valid.loc[index]
            selections.append({
                "threshold": threshold,
                "metric": metric,
                "selection": direction,
                "K": int(selected["K"]),
                "score": float(selected[metric]),
                "actual_clusters": int(selected["actual_clusters"]),
                "threshold_items": int(selected["threshold_items"]),
            })
    return metrics, pd.DataFrame(selections)


def save_overlap_outputs(membership, ids, best_k):
    overlap_results = []
    for threshold in OVERLAP_THRESHOLDS:
        binary_membership = (membership >= threshold).astype(int)
        valid_clusters = np.where(binary_membership.sum(axis=0) >= 1)[0]
        binary_membership = binary_membership[:, valid_clusters]
        membership_count = binary_membership.sum(axis=1)
        label = f"{threshold:.2f}".replace(".", "_")

        pd.DataFrame(
            binary_membership,
            index=ids,
            columns=[f"Cluster_{index + 1}" for index in valid_clusters],
        ).to_csv(os.path.join(OUT_DIR, f"overlap_membership_threshold_{label}_K{best_k}.csv"))

        assignments = []
        for output_index, source_index in enumerate(valid_clusters):
            for item_index in np.where(membership[:, source_index] >= threshold)[0]:
                assignments.append({
                    "threshold": threshold,
                    "K": best_k,
                    "cluster": f"Cluster_{output_index + 1}",
                    "intelligence_id": ids[item_index],
                    "membership": float(membership[item_index, source_index]),
                })
        pd.DataFrame(assignments, columns=["threshold", "K", "cluster", "intelligence_id", "membership"]).to_csv(
            os.path.join(OUT_DIR, f"cluster_assignments_threshold_{label}_K{best_k}.csv"),
            index=False,
        )
        overlap_results.append({
            "threshold": threshold,
            "K": best_k,
            "actual_clusters": binary_membership.shape[1],
            "overlap_ratio": float(np.mean(membership_count > 1)),
            "average_cluster_memberships": float(np.mean(membership_count)),
        })

    pd.DataFrame(overlap_results).to_csv(
        os.path.join(OUT_DIR, "overlap_threshold_summary.csv"), index=False
    )


def run_insight_analysis(membership_path, assignment_paths):
    analyzer_path = os.path.join(BASE_DIR, "archive", "analyze_cluster_insights.py")
    if os.path.exists(analyzer_path):
        subprocess.run([
            sys.executable, analyzer_path,
            "--membership-file", membership_path,
            "--approach", "fcm_llm_primary"], check=True)
        for threshold, assignment_path in assignment_paths:
            if not os.path.exists(assignment_path) or os.path.getsize(assignment_path) == 0:
                print(f"Skipping empty assignment file: {assignment_path}")
                continue
            subprocess.run([
                sys.executable, analyzer_path,
                "--assignments-file", assignment_path,
                "--approach", f"fcm_llm_threshold_{threshold:.2f}"], check=True)


if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(f"Similarity matrix CSV not found at: {CSV_FILE}")

df = pd.read_csv(CSV_FILE, index_col=0)
ids = df.index.astype(str).tolist()
similarity = np.nan_to_num(df.values.astype(float), nan=0.0, posinf=1.0, neginf=0.0)
similarity = np.clip((similarity + similarity.T) / 2.0, 0.0, 1.0)
np.fill_diagonal(similarity, 1.0)
if similarity.shape[0] != similarity.shape[1]:
    raise ValueError("Similarity matrix must be square.")

N = len(similarity)
similarity_boosted = np.power(similarity, SIMILARITY_POWER)
distance = 1.0 - similarity_boosted
np.fill_diagonal(distance, 0.0)

coordinates = MDS(
    n_components=min(10, N - 1),
    metric="precomputed",
    random_state=RANDOM_SEED,
).fit_transform(distance)
features = StandardScaler().fit_transform(coordinates)

pd.DataFrame(
    similarity_boosted,
    index=ids,
    columns=ids,
).to_csv(os.path.join(OUT_DIR, "boosted_similarity_matrix.csv"))

results = []
membership_results = {}
for cluster_count in range(2, (N // 3) + 1):
    best = run_best_fcm(features, cluster_count)
    membership = best["membership"].T
    labels = np.argmax(membership, axis=1)
    fuzzy_sil = fuzzy_silhouette(distance, membership)
    if len(np.unique(labels)) > 1:
        ordinary_sil = silhouette_score(distance, labels, metric="precomputed")
        db = davies_bouldin_score(features, labels)
        ch = calinski_harabasz_score(features, labels)
    else:
        ordinary_sil = db = ch = np.nan
    results.append({"K": cluster_count, "fpc": best["fpc"], "fuzzy_silhouette": fuzzy_sil, "silhouette": ordinary_sil, "davies_bouldin": db, "calinski_harabasz": ch})
    membership_results[cluster_count] = membership

results_df = pd.DataFrame(results)
threshold_metrics, threshold_selections = evaluate_thresholds(
    distance, features, membership_results
)
if threshold_selections.empty:
    raise ValueError(f"No threshold metrics could be calculated for K >= {MIN_CLUSTER_K}.")
threshold_metrics.to_csv(os.path.join(OUT_DIR, "threshold_performance_metrics.csv"), index=False)
threshold_selections.to_csv(os.path.join(OUT_DIR, "threshold_metric_k_selection.csv"), index=False)
full_candidates = results_df[
    (results_df["K"] >= MIN_CLUSTER_K)
    & results_df["fuzzy_silhouette"].notna()
]
if full_candidates.empty:
    raise ValueError(f"No full-data fuzzy silhouette values found for K >= {MIN_CLUSTER_K}.")
best_selection = full_candidates.loc[full_candidates["fuzzy_silhouette"].idxmax()]
best_k = int(best_selection["K"])
best_score = float(best_selection["fuzzy_silhouette"])
best_membership = membership_results[best_k]

results_df.to_csv(os.path.join(OUT_DIR, "clustering_metrics.csv"), index=False)
membership_path = os.path.join(OUT_DIR, "fuzzy_membership_matrix.csv")
pd.DataFrame(best_membership, index=ids, columns=[f"Cluster_{index + 1}" for index in range(best_k)]).to_csv(membership_path)
save_overlap_outputs(best_membership, ids, best_k)

plt.figure(figsize=(10, 6), dpi=160)
for metric, marker in (("fuzzy_silhouette", "o"), ("silhouette", "s")):
    plt.plot(results_df["K"], results_df[metric], marker=marker, label=metric)
plt.axvline(best_k, color="black", linestyle="--", label=f"Selected K = {best_k}")
plt.axvline(MIN_CLUSTER_K, color="gray", linestyle=":", label=f"Minimum considered K = {MIN_CLUSTER_K}")
plt.xlabel("Number of clusters (K)")
plt.ylabel("Score")
plt.title("FCM-LLM clustering performance")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "clustering_metrics.png"), dpi=300)
plt.savefig(os.path.join(OUT_DIR, "clustering_metrics.pdf"), dpi=300)
plt.close()

plt.figure(figsize=(12, 8), dpi=160)
plt.imshow(best_membership, aspect="auto", interpolation="nearest", cmap="viridis")
plt.colorbar(label="Membership")
plt.xlabel("Cluster")
plt.ylabel("Intelligence item")
plt.title(f"FCM-LLM fuzzy membership matrix (K={best_k})")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "membership_heatmap.png"), dpi=300)
plt.savefig(os.path.join(OUT_DIR, "membership_heatmap.pdf"), dpi=300)
plt.close()

print(results_df.to_string(index=False))
print(threshold_selections.to_string(index=False))
if best_score < 0:
    print(f"WARNING: best full-data fuzzy silhouette is negative ({best_score:.6f}); clustering separation is weak.")
print(f"Selected K by full-data fuzzy silhouette among K >= {MIN_CLUSTER_K}: {best_k} (score={best_score:.6f})")
print(f"Saved metrics, overlap outputs, diagrams, and membership matrix to {OUT_DIR}")
run_insight_analysis(membership_path, [
    (threshold, os.path.join(OUT_DIR, f"cluster_assignments_threshold_{threshold:.2f}".replace(".", "_") + f"_K{best_k}.csv"))
    for threshold in OVERLAP_THRESHOLDS
])
