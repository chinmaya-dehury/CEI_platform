import os

import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure"
COSINE_FILE = os.path.join(
    BASE_DIR, "results", "result_cosine_fcm", "clustering_metrics.csv"
)
LLM_FILE = os.path.join(
    BASE_DIR, "results", "result_llm_fcm", "clustering_metrics.csv"
)
OUTPUT_DIR = os.path.join(BASE_DIR, "results", "comparison")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_metrics(path, name):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Metrics file not found: {path}")
    metrics = pd.read_csv(path)
    required_columns = {"K", "fuzzy_silhouette"}
    missing_columns = required_columns - set(metrics.columns)
    if missing_columns:
        raise ValueError(f"{path} is missing columns: {sorted(missing_columns)}")
    metrics = metrics[["K", "fuzzy_silhouette"]].dropna()
    if metrics.empty:
        raise ValueError(f"No fuzzy silhouette values found in {path}")
    metrics["K"] = metrics["K"].astype(int)
    metrics["method"] = name
    return metrics


cosine_metrics = load_metrics(COSINE_FILE, "Cosine FCM")
llm_metrics = load_metrics(LLM_FILE, "LLM FCM")

cosine_best = cosine_metrics.loc[cosine_metrics["fuzzy_silhouette"].idxmax()]
llm_best = llm_metrics.loc[llm_metrics["fuzzy_silhouette"].idxmax()]

plt.figure(figsize=(14, 8), dpi=200)
plt.plot(
    cosine_metrics["K"],
    cosine_metrics["fuzzy_silhouette"],
    color="#1769aa",
    marker="o",
    linewidth=3,
    label="Cosine similarity FCM",
)
plt.plot(
    llm_metrics["K"],
    llm_metrics["fuzzy_silhouette"],
    color="#d95f02",
    marker="s",
    linewidth=3,
    label="LLM Similarity FCM",
)

plt.scatter(
    cosine_best["K"],
    cosine_best["fuzzy_silhouette"],
    color="#1769aa",
    edgecolor="black",
    s=130,
    zorder=5,
    label=f"Cosine best K={int(cosine_best['K'])}",
)
plt.scatter(
    llm_best["K"],
    llm_best["fuzzy_silhouette"],
    color="#d95f02",
    edgecolor="black",
    s=130,
    zorder=5,
    label=f"LLM best K={int(llm_best['K'])}",
)

plt.annotate(
    f"K={int(cosine_best['K'])}\n{cosine_best['fuzzy_silhouette']:.4f}",
    (cosine_best["K"], cosine_best["fuzzy_silhouette"]),
    xytext=(8, 12),
    textcoords="offset points",
    color="#1769aa",
    fontweight="bold",
    fontsize=12,
)
plt.annotate(
    f"K={int(llm_best['K'])}\n{llm_best['fuzzy_silhouette']:.4f}",
    (llm_best["K"], llm_best["fuzzy_silhouette"]),
    xytext=(0, -42),
    textcoords="offset points",
    color="#d95f02",
    fontweight="bold",
    ha="center",
    fontsize=12,
)

plt.xlabel("Number of clusters (K)", fontsize=18, fontweight="bold")
plt.ylabel("Fuzzy silhouette score", fontsize=18, fontweight="bold")
plt.title(
    "Fuzzy Silhouette Score vs. Number of Clusters",
    fontsize=22,
    fontweight="bold",
)
plt.xticks(fontsize=15, fontweight="bold")
plt.yticks(fontsize=15, fontweight="bold")
plt.grid(alpha=0.3)
legend = plt.legend(fontsize=15, framealpha=0.95)
for legend_text in legend.get_texts():
    legend_text.set_fontweight("bold")
plt.tight_layout()

png_path = os.path.join(OUTPUT_DIR, "fuzzy_silhouette_comparison.png")
pdf_path = os.path.join(OUTPUT_DIR, "fuzzy_silhouette_comparison.pdf")
plt.savefig(png_path, dpi=300, bbox_inches="tight")
plt.savefig(pdf_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"Cosine FCM best K: {int(cosine_best['K'])}, score: {cosine_best['fuzzy_silhouette']:.6f}")
print(f"LLM FCM best K: {int(llm_best['K'])}, score: {llm_best['fuzzy_silhouette']:.6f}")
print(f"Saved PNG: {png_path}")
print(f"Saved PDF: {pdf_path}")
