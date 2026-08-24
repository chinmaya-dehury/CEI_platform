import pandas as pd
import matplotlib.pyplot as plt
import os

# Load data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE_DIR, "sensitivity_results.csv"))

# Create output directory for plots
plots_dir = os.path.join(BASE_DIR, "plots")
os.makedirs(plots_dir, exist_ok=True)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.patch.set_facecolor('white')

# 1. Theta 2 (TR Threshold) vs Active Agents
t2_summary = df.groupby('Theta_2')['Active_Agents'].mean().reset_index()
axes[0].plot(t2_summary['Theta_2'], t2_summary['Active_Agents'], marker='o', color='blue', linewidth=2.5)
axes[0].set_title('Impact of $\\theta_T$ on Agent Recall', fontsize=14)
axes[0].set_xlabel('Task Relevance Threshold ($\\theta_T$)', fontsize=12)
axes[0].set_ylabel('Active Agents (Survivors)', fontsize=12)
axes[0].axvline(x=0.40, color='red', linestyle='--', label='Chosen $\\theta_T = 0.40$')
axes[0].grid(True, linestyle='--', alpha=0.7)
axes[0].legend()

# 2. Theta 1 (SR Threshold) vs Cluster Size
# Fix Alpha, Beta, Gamma to defaults to observe pure Theta_1 impact
default_weights = df[(df['Alpha'] == 0.5) & (df['Beta'] == 0.3) & (df['Gamma'] == 0.2)]
t1_summary = default_weights.groupby('Theta_1')['Avg_Cluster_Size'].mean().reset_index()
axes[1].plot(t1_summary['Theta_1'], t1_summary['Avg_Cluster_Size'], marker='s', color='green', linewidth=2.5)
axes[1].set_title('Impact of $\\theta_S$ on Cluster Precision', fontsize=14)
axes[1].set_xlabel('Semantic Relationship Threshold ($\\theta_S$)', fontsize=12)
axes[1].set_ylabel('Average Cluster Size', fontsize=12)
axes[1].axvline(x=0.80, color='red', linestyle='--', label='Chosen $\\theta_S = 0.80$')
axes[1].grid(True, linestyle='--', alpha=0.7)
axes[1].legend()

# 3. Alpha (Task Weight) vs Cluster Coherence
# Fix Thetas to chosen values
fixed_thetas = df[(df['Theta_1'] == 0.8) & (df['Theta_2'] == 0.4)]
alpha_summary = fixed_thetas.groupby('Alpha')['Avg_Cluster_Size'].mean().reset_index()
axes[2].plot(alpha_summary['Alpha'], alpha_summary['Avg_Cluster_Size'], marker='^', color='purple', linewidth=2.5)
axes[2].set_title('Impact of Task Weight ($\\alpha$) on Clustering', fontsize=14)
axes[2].set_xlabel('Task Similarity Weight ($\\alpha$)', fontsize=12)
axes[2].set_ylabel('Average Cluster Size', fontsize=12)
axes[2].axvline(x=0.50, color='red', linestyle='--', label='Chosen $\\alpha = 0.50$')
axes[2].grid(True, linestyle='--', alpha=0.7)
axes[2].legend()

plt.tight_layout()
output_path = os.path.join(plots_dir, "sensitivity_analysis.png")
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Graphs successfully generated and saved to: {output_path}")
