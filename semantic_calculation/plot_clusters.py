import json
import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sentence_transformers import SentenceTransformer
import warnings
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings('ignore')

# 1. Load Data
model = SentenceTransformer('all-mpnet-base-v2')

with open('intelligence_metadata.json', 'r') as f:
    intelligences = json.load(f)

with open('example.txt', 'r') as f:
    tasks = [line.strip() for line in f if line.strip()][:20]

# 2. Extract texts and map domains correctly
agent_texts = []
agent_domains = []

def extract_base_domain(long_domain_str):
    mapping = {
        "Environment": "Environment",
        "Transportation": "Transportation",
        "DisasterManagement": "Disaster Management",
        "SmartBuilding": "Smart Building",
        "Energy": "Energy",
        "Agriculture": "Agriculture",
        "Manufacturing": "Manufacturing",
        "Healthcare": "Healthcare",
        "healtcare": "Healthcare"
    }
    for key, val in mapping.items():
        if key.lower() in long_domain_str.lower():
            return val
    return "Other"

for intel in intelligences:
    tasks_str = ", ".join([str(t) for t in intel.get("tasks", [])])
    identity = f"Intelligence: {intel['name']}. Domain: {intel['domain']}. Context: {intel['context']}. Description: {intel.get('description', '')}. Tasks: {tasks_str}."
    agent_texts.append(identity)
    agent_domains.append(extract_base_domain(intel['domain']))

# 3. Compute Embeddings
print("Computing embeddings...")
agent_embeddings = model.encode(agent_texts)
task_embeddings = model.encode(tasks)

all_embeddings = np.vstack([agent_embeddings, task_embeddings])

print("Running t-SNE...")
tsne = TSNE(n_components=2, perplexity=15, random_state=42, init='pca')
all_2d = tsne.fit_transform(all_embeddings)

agent_2d = all_2d[:len(intelligences)]
task_2d = all_2d[len(intelligences):]

# 4. Plotting Setup (Publication Ready)
plt.style.use('default')
fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

unique_domains = list(set(agent_domains))
cmap = plt.get_cmap('tab10')
colors = [cmap(i) for i in np.linspace(0, 1, len(unique_domains))]
domain_color_map = dict(zip(unique_domains, colors))

# Plot agents with much larger markers and bold colors
for domain in unique_domains:
    idx = [i for i, d in enumerate(agent_domains) if d == domain]
    ax.scatter(agent_2d[idx, 0], agent_2d[idx, 1], 
               c=[domain_color_map[domain]], label=domain, 
               alpha=0.9, edgecolors='black', linewidth=0.5, s=120, zorder=2)

# Plot tasks with larger, visible stars
ax.scatter(task_2d[:, 0], task_2d[:, 1], 
           c='black', marker='*', s=350, edgecolor='gold', linewidth=1.5,
           label='Benchmark Tasks', zorder=4)

# Draw distinct connections
sim_matrix = cosine_similarity(task_embeddings, agent_embeddings)
for t_idx in range(len(tasks)):
    top_3 = np.argsort(sim_matrix[t_idx])[-3:]
    for a_idx in top_3:
        ax.plot([task_2d[t_idx, 0], agent_2d[a_idx, 0]], 
                [task_2d[t_idx, 1], agent_2d[a_idx, 1]], 
                color='gray', linestyle='--', alpha=0.5, linewidth=1.2, zorder=1)

# Formatting - Restore X and Y axes
ax.set_title("Semantic Space: Intelligence Agents vs. Benchmark Tasks", fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel("t-SNE Dimension 1", fontsize=12, fontweight='bold')
ax.set_ylabel("t-SNE Dimension 2", fontsize=12, fontweight='bold')
ax.grid(True, linestyle=':', alpha=0.6, zorder=0)

# Make axes ticks visible
ax.tick_params(axis='both', which='major', labelsize=10)

# Legend outside to save space, but larger text
ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=10, title="Domains", title_fontsize=12, frameon=True, shadow=True)

plt.tight_layout()
output_file_pdf = "semantic_space_plot.pdf"
output_file_png = "semantic_space_plot.png"
plt.savefig(output_file_pdf, bbox_inches='tight', dpi=300)
plt.savefig(output_file_png, bbox_inches='tight', dpi=300)
print(f"Plots saved to {output_file_pdf} and {output_file_png}")
