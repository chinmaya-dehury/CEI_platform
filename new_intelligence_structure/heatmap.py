import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure\similarity_results\cosine_experiment\similarity_matrix.csv"

#CSV_FILE = r"C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure\similarity_results\llm_experiment\llm_similarity_matrix.csv"
S = pd.read_csv(CSV_FILE, index_col=0)
OUTPUT_DIR = os.path.dirname(CSV_FILE)

# Use each pair once, exclude diagonal self-similarity scores, and ignore
# very low similarity values below 0.30.
similarity_scores = S.to_numpy(dtype=float)
upper_triangle = np.triu_indices_from(similarity_scores, k=1)
all_pairwise_scores = similarity_scores[upper_triangle]
pairwise_scores = all_pairwise_scores[all_pairwise_scores >= 0.20]

medium_scores = (all_pairwise_scores >= 0.50) & (all_pairwise_scores < 0.75)
high_scores = all_pairwise_scores >= 0.75
low_scores = all_pairwise_scores < 0.50
total_pairs = len(all_pairwise_scores)
filtered_pairs = len(pairwise_scores)

print("\n--- Similarity Score Distribution ---")
print(f"Intelligences: {len(S)}")
print(f"Total unique pairs: {total_pairs}")
print(f"Ignored pairs below 0.20: {total_pairs - filtered_pairs}")
print(f"Pairs included in histogram (>=0.20): {filtered_pairs}")
print(
    f"Low similarity (<0.50): "
    f"{low_scores.sum()} ({low_scores.mean() * 100:.2f}% of all pairs)"
)
print(
	f"Medium similarity (0.50-<0.75): "
	f"{medium_scores.sum()} ({medium_scores.mean() * 100:.2f}% of all pairs)"
)
print(
	f"High similarity (>=0.75): "
	f"{high_scores.sum()} ({high_scores.mean() * 100:.2f}% of all pairs)"
)

plt.figure(figsize=(10, 8))
plt.imshow(S, cmap="viridis", vmin=0, vmax=1, aspect="auto")
plt.colorbar(label="Similarity")
plt.title("Cosine Similarity Matrix")
plt.xlabel("Intelligence")
plt.ylabel("Intelligence")
plt.tight_layout()
heat_path = os.path.join(OUTPUT_DIR, "cosine_similarity_matrix.png")
#heat_path = os.path.join(OUTPUT_DIR, "llm_similarity_matrix.png")
plt.savefig(heat_path, dpi=300, bbox_inches="tight")
plt.show()

plt.figure(figsize=(10, 6))
counts, bin_edges, bars = plt.hist(pairwise_scores, bins=np.linspace(0.20, 1, 15),color="steelblue",edgecolor="white",)
plt.axvspan(0.50, 0.75, color="orange", alpha=0.20, label="Medium: 0.50-<0.75")
plt.axvspan(0.75, 1.00, color="red", alpha=0.15, label="High: >=0.75")
plt.xlim(0.20, 1)
plt.xticks(np.arange(0.20, 1.01, 0.05), rotation=45)
plt.xlabel("Pairwise Cosine Similarity Score")
#plt.xlabel("Pairwise llm Similarity Score")
plt.ylabel("Number of Pairs")
plt.title("Distribution of Pairwise Cosine Similarity Scores")
#plt.title("Distribution of Pairwise llm Similarity Scores")
plt.grid(axis="y", alpha=0.25)
plt.legend()

for count, bar in zip(counts, bars):

	if count > 0:
		plt.text(
			bar.get_x() + bar.get_width() / 2,
			count,
			f"{int(count)}",
			ha="center",
			va="bottom",
			fontsize=8,
		)

plt.tight_layout()
histogram_path = os.path.join(OUTPUT_DIR, "cosine_similarity_histogram.png")
#histogram_path = os.path.join(OUTPUT_DIR, "llm_similarity_histogram.png")
plt.savefig(histogram_path, dpi=300, bbox_inches="tight")
print(f"Saved similarity histogram to: {histogram_path}")
plt.show()
