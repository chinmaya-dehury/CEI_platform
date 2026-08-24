import json
import os
import numpy as np
from itertools import combinations
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTELLIGENCE_FILE = os.path.join(BASE_DIR, "intelligence_metadata.json")
EXAMPLE_FILE = os.path.join(BASE_DIR, "example.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "sensitivity_results.csv")

print("Loading model and data...")
model = SentenceTransformer("all-mpnet-base-v2")

with open(INTELLIGENCE_FILE, "r") as f:
    intelligences = json.load(f)

# 1. PRE-CALCULATE ALL VECTORS & SIMILARITIES
for intel in intelligences:
    intel["_context_vector"] = model.encode(intel.get("context", "")).reshape(1, -1)
    intel["_domain_vector"] = model.encode(intel.get("domain", "")).reshape(1, -1)
    
    tasks_list = intel.get("tasks", [])
    if not tasks_list:
        intel["_tasks_vector"] = np.zeros((1, 384))
    else:
        task_texts = [f"Task: {t.get('name', '')}. Description: {t.get('description', '')}" if isinstance(t, dict) else str(t) for t in tasks_list]
        intel["_tasks_vector"] = np.mean(model.encode(task_texts), axis=0).reshape(1, -1)
        
    intel["_identity_text"] = f"Intelligence: {intel['name']}. Domain: {intel['domain']}. Context: {intel['context']}."
    intel["_identity_vector"] = model.encode(intel["_identity_text"]).reshape(1, -1)

# Pre-calculate pairwise similarities
n = len(intelligences)
sim_task = np.zeros((n, n))
sim_context = np.zeros((n, n))
sim_domain = np.zeros((n, n))

print("Pre-computing pairwise similarities...")
for i in range(n):
    for j in range(i+1, n):
        st = cosine_similarity(intelligences[i]["_tasks_vector"], intelligences[j]["_tasks_vector"])[0][0]
        sc = cosine_similarity(intelligences[i]["_context_vector"], intelligences[j]["_context_vector"])[0][0]
        sd = cosine_similarity(intelligences[i]["_domain_vector"], intelligences[j]["_domain_vector"])[0][0]
        
        sim_task[i, j] = sim_task[j, i] = st
        sim_context[i, j] = sim_context[j, i] = sc
        sim_domain[i, j] = sim_domain[j, i] = sd

# Read ONE sample task for the sweep
with open(EXAMPLE_FILE, "r") as f:
    target_task_text = f.readline().strip()

target_task_vector = model.encode(target_task_text).reshape(1, -1)

# Pre-compute TR scores for all intelligences against the target task
tr_scores = np.zeros(n)
for i in range(n):
    tr_scores[i] = cosine_similarity(target_task_vector, intelligences[i]["_identity_vector"])[0][0]

# 2. DEFINE PARAMETER RANGES
theta_2_range = np.arange(0.30, 0.65, 0.05)
theta_1_range = np.arange(0.60, 0.95, 0.05)

# Generate simplex weights (alpha + beta + gamma = 1) step 0.1
weights = []
for a in range(11):
    for b in range(11 - a):
        c = 10 - a - b
        weights.append((a/10.0, b/10.0, c/10.0))

print(f"Running grid sweep for {len(theta_2_range) * len(theta_1_range) * len(weights)} combinations...")

# 3. RUN FAST GRID SWEEP
results = []
for t2 in theta_2_range:
    # Filter active agents (TR >= theta_2)
    active_indices = np.where(tr_scores >= t2)[0]
    num_survivors = len(active_indices)
    
    if num_survivors == 0:
        continue
        
    for t1 in theta_1_range:
        for (alpha, beta, gamma) in weights:
            # Create edges
            edges = []
            for i_idx in range(num_survivors):
                for j_idx in range(i_idx + 1, num_survivors):
                    u = active_indices[i_idx]
                    v = active_indices[j_idx]
                    
                    sr = (alpha * sim_task[u, v]) + (beta * sim_context[u, v]) + (gamma * sim_domain[u, v])
                    if sr >= t1:
                        edges.append((u, v))
            
            # Clustering (connected components)
            clusters = []
            visited = set()
            active_set = set(active_indices)
            
            # Form graph
            adj = {u: set() for u in active_indices}
            for u, v in edges:
                adj[u].add(v)
                adj[v].add(u)
                
            for u in active_indices:
                if u not in visited:
                    cluster = set()
                    queue = [u]
                    while queue:
                        curr = queue.pop(0)
                        if curr not in visited:
                            visited.add(curr)
                            cluster.add(curr)
                            for neighbor in adj[curr]:
                                if neighbor not in visited:
                                    queue.append(neighbor)
                    clusters.append(cluster)
            
            multi_clusters = [c for c in clusters if len(c) > 1]
            num_clusters = len(multi_clusters)
            avg_size = np.mean([len(c) for c in multi_clusters]) if num_clusters > 0 else 0
            
            results.append({
                "Theta_2": round(t2, 2),
                "Theta_1": round(t1, 2),
                "Alpha": alpha,
                "Beta": beta,
                "Gamma": gamma,
                "Active_Agents": num_survivors,
                "Multi_Agent_Clusters": num_clusters,
                "Avg_Cluster_Size": round(avg_size, 2)
            })

# 4. SAVE AND INTERPRET
df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False)
print(f"Grid sweep complete. Saved {len(df)} records to {OUTPUT_FILE}")
