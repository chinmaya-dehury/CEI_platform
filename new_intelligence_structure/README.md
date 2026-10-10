# Edge Intelligence Generation & Clustering Platform

This folder (`new_intelligence_structure`) contains the core dataset of edge intelligence JSON definitions and the complete Python suite for calculating semantic/LLM-based pairwise distances, clustering those intelligences, and generating visual insights.

---

## 📂 Folder Structure

| Folder | Description |
| :--- | :--- |
| **`dataset/`** | The ground truth directory containing all 100+ generated intelligence JSON files, organized into domain subfolders (e.g., Agriculture, Healthcare, Transportation). |
| **`results/`** | The primary output directory for clustering algorithms. It contains subfolders for each approach (e.g., `result_cosine_fcm`, `result_llm_baseline`), containing `fuzzy_membership_matrix.csv`, and a `cluster_insights/` folder where visual grid graphs are saved. |
| **`similarity_results/`** | Stores the heavy \(N \times N\) pairwise similarity matrices as numpy (`.npy`) and CSV files. This includes LLM experiment outputs and feature-based distance calculations (`D_text`, `D_cat`, `sim_final`). |
| **`archive/`** | Contains data generation scripts, one-off cleanup scripts, schema validators, and the visualization tools for graphing cluster insights. |

---

## 🏃 Workflow & Python Scripts

The pipeline is generally executed in the following sequential phases:

### Phase 1: Similarity Matrix Generation (Root Folder)
Before clustering, we calculate how similar every intelligence item is to every other item using two distinct approaches:

| Script | Output Location | Description |
| :--- | :--- | :--- |
| **`similarity_cosine_pairwsie.py`** | `similarity_results/*.npy` | Embeds text using `sentence-transformers`, calculates tag Jaccard & Domain distances, performs a grid search for optimal weights, and saves feature-based distance matrices. |
| **`similarity_llm_pairwise.py`** | `similarity_results/llm_experiment/*.npy` | Uses Ollama LLM to cognitively score semantic and contextual complementarity between pairs, generating an LLM-based similarity matrix. |
| **`export_matrix.py`** | `similarity_results/sim_final.csv` | Utility script to convert the `.npy` matrix into an Excel-readable `.csv`. |
| **`heatmap.py`** | *Displays Plot* | Visualizes the pairwise distance matrices as heatmaps. |

### Phase 2: Fuzzy C-Means & Baseline Clustering (Root Folder)
Using the precomputed distance matrices, these scripts organize the intelligences into overlapping clusters:

| Script | Output Location | Description |
| :--- | :--- | :--- |
| **`fcm_cosine.py`** | `results/result_cosine_fcm/` | Performs Fuzzy C-Means (FCM) clustering on the feature-based (cosine) distance matrix. Outputs the `fuzzy_membership_matrix.csv`. |
| **`fcm_llm.py`** | `results/result_llm_fcm/` | Performs FCM clustering on the LLM-derived distance matrix. Outputs the `fuzzy_membership_matrix.csv`. |
| **`baseline_fcmeans_cosine.py`** | `results/result_cosine_baseline_corrected/` | Baseline strict (hard) clustering for feature-based similarities. |
| **`baseline_fcmeans_llm.py`** | `results/result_llm_baseline/` | Baseline strict (hard) clustering for LLM-based similarities. |
| **`compare_fuzzy_silhouette.py`** | Console Output | Utility to compare clustering performance using Silhouette Scores. |

### Phase 3: Cluster Visualization & Insights (`archive/`)
These scripts read the `fuzzy_membership_matrix.csv` files generated in Phase 2 to plot the final visual outputs.

| Script | Output Location | Description |
| :--- | :--- | :--- |
| **`archive/analyze_cluster_insights.py`** | `results/cluster_insights/` | Analyzes *feature-based* clusters (`fcm_cosine`). Generates a 4-column wide domain distribution graph (`.png`/`.pdf`) and bar charts, alongside querying the LLM for text insights. |
| **`archive/analyze_cluster_insights_llm.py`**| `results/cluster_insights/` | Analyzes *LLM-based* clusters (`fcm_llm_standard`). Generates a 9-column wide domain distribution graph (`.png`/`.pdf`), filtering out noisy clusters with less than 2 items. |

### Utility & Data Management (`archive/`)
Scripts previously used to generate, clean, and validate the `dataset/` JSON files:

| Script | Description |
| :--- | :--- |
| **`archive/generate_intelligences.py`** | Automated LLM script to generate new intelligence JSONs from scratch. |
| **`archive/Validation.py`** | Ensures all JSON files rigidly adhere to the expected JSON schema. |
| **`archive/extract_intelligence_summary.py`** | Dumps Domain, Name, and Description of all items into `intelligence_summary.csv`. |
| **`archive/update_context_from_csv.py`** | Bulk updates intelligence content using CSV rules. |
| **`tags_unique.py`** *(Root)* | Simple script to extract and analyze the unique tags utilized across the dataset. |
