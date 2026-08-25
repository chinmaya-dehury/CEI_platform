import json
import os
import numpy as np
import pandas as pd
from itertools import combinations
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import f1_score, adjusted_rand_score
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTELLIGENCE_FILE = os.path.join(BASE_DIR, "intelligence_metadata.json")
GT_FILE = os.path.join(BASE_DIR, "expert_ground_truth.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "gt_sensitivity_results.csv")

if not os.path.exists(GT_FILE):
    print("Please ensure expert_ground_truth.json exists.")
    exit(1)

with open(GT_FILE, "r") as f:
    ground_truths_data = json.load(f)

with open(INTELLIGENCE_FILE, "r") as f:
    intelligences = json.load(f)

print("Loading model...")
model = SentenceTransformer("all-mpnet-base-v2")

# Precompute embeddings
for intel in intelligences:
    intel["_context_vector"] = model.encode(intel.get("context", "")).reshape(1, -1)
    intel["_domain_vector"] = model.encode(intel.get("domain", "")).reshape(1, -1)
    tasks_list = intel.get("tasks", [])
    if not tasks_list:
        intel["_tasks_vector"] = np.zeros((1, 384))
    else:
        task_texts = [f"Task: {t.get('name', '')}. Description: {t.get('description', '')}" if isinstance(t, dict) else str(t) for t in tasks_list]
        intel["_tasks_vector"] = np.mean(model.encode(task_texts), axis=0).reshape(1, -1)
        
    intel["_identity_text"] = f"Intelligence: {intel['name']}. Domain: {intel['domain']}. Context: {intel['context']}. Description: {intel['description']}"
    intel["_identity_vector"] = model.encode(intel["_identity_text"]).reshape(1, -1)

n = len(intelligences)
agent_ids = [intel["id"] for intel in intelligences]

print("Precomputing pairwise similarities...")
sim_task = np.zeros((n, n))
sim_context = np.zeros((n, n))
sim_domain = np.zeros((n, n))
for i in range(n):
    for j in range(i+1, n):
        st = cosine_similarity(intelligences[i]["_tasks_vector"], intelligences[j]["_tasks_vector"])[0][0]
        sc = cosine_similarity(intelligences[i]["_context_vector"], intelligences[j]["_context_vector"])[0][0]
        sd = cosine_similarity(intelligences[i]["_domain_vector"], intelligences[j]["_domain_vector"])[0][0]
        sim_task[i, j] = sim_task[j, i] = st
        sim_context[i, j] = sim_context[j, i] = sc
        sim_domain[i, j] = sim_domain[j, i] = sd

# Generate Param Grid
param_grid = []
theta_t_list = np.arange(0.20, 0.55, 0.05)
theta_s_list = np.arange(0.50, 0.85, 0.05)

# Generate simplex weights alpha > beta > gamma with step 0.05
weights = []
for a_int in range(10, 17):  # 10 * 0.05 = 0.50, 16 * 0.05 = 0.80
    a = a_int * 0.05
    rem = 20 - a_int
    for b_int in range(1, rem):
        g_int = rem - b_int
        if a_int > b_int and b_int > g_int:
            weights.append((round(a, 2), round(b_int * 0.05, 2), round(g_int * 0.05, 2)))

for t_t in theta_t_list:
    for t_s in theta_s_list:
        for w in weights:
            param_grid.append({"theta_t": round(t_t, 2), "theta_s": round(t_s, 2), "alpha": w[0], "beta": w[1], "gamma": w[2]})

def get_ari(predicted_clusters, expected_clusters, all_agents_set):
    labels_true = {agent: -1 for agent in all_agents_set}
    labels_pred = {agent: -1 for agent in all_agents_set}
    for c_id, cluster in enumerate(expected_clusters):
        for agent in cluster: labels_true[agent] = c_id
    for c_id, cluster in enumerate(predicted_clusters):
        for agent in cluster: labels_pred[agent] = c_id
    y_true = [labels_true[a] for a in all_agents_set]
    y_pred = [labels_pred[a] for a in all_agents_set]
    return adjusted_rand_score(y_true, y_pred)

results = []
print(f"Evaluating {len(param_grid)} Configurations...")

# Precompute TR scores for all tasks to save time
for gt in ground_truths_data:
    task_vec = model.encode(gt["task_text"]).reshape(1, -1)
    gt["tr_scores"] = np.array([cosine_similarity(task_vec, intel["_identity_vector"])[0][0] for intel in intelligences])

for config_idx, config in enumerate(param_grid):
    t_t, t_s = config["theta_t"], config["theta_s"]
    alpha, beta, gamma = config["alpha"], config["beta"], config["gamma"]
    
    config_tr_f1 = []
    config_ari = []
    config_ari_gt = []
    
    for gt in ground_truths_data:
        expected_candidates = set(gt["expected_candidates"])
        expected_clusters = [set(c) for c in gt["expected_clusters"]]
        
        tr_scores = gt["tr_scores"]
        active_indices = np.where(tr_scores >= t_t)[0]
        predicted_candidates = set([agent_ids[i] for i in active_indices])
        
        y_true_tr = [1 if a in expected_candidates else 0 for a in agent_ids]
        y_pred_tr = [1 if a in predicted_candidates else 0 for a in agent_ids]
        tr_f1 = f1_score(y_true_tr, y_pred_tr, zero_division=0)
        config_tr_f1.append(tr_f1)
        
        edges = []
        for i_idx in range(len(active_indices)):
            for j_idx in range(i_idx + 1, len(active_indices)):
                u, v = active_indices[i_idx], active_indices[j_idx]
                sr = (alpha * sim_task[u, v]) + (beta * sim_context[u, v]) + (gamma * sim_domain[u, v])
                if sr >= t_s:
                    edges.append((u, v))
                    
        clusters = []
        visited = set()
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
                            if neighbor not in visited: queue.append(neighbor)
                clusters.append(set([agent_ids[x] for x in cluster]))
                
        eval_agents_all = expected_candidates.union(predicted_candidates)
        eval_agents_gt = expected_candidates

        ari_all = get_ari(clusters, expected_clusters, eval_agents_all) if eval_agents_all else (1.0 if not expected_candidates else 0.0)
        
        # Calculate ARI only for the expected GT candidates
        if eval_agents_gt:
            # Re-filter clusters to only include GT candidates
            filtered_clusters = [c.intersection(eval_agents_gt) for c in clusters]
            filtered_clusters = [c for c in filtered_clusters if c]
            ari_gt = get_ari(filtered_clusters, expected_clusters, eval_agents_gt)
        else:
            ari_gt = 1.0
            
        config_ari.append(ari_all)
        config_ari_gt.append(ari_gt)
        
    results.append({
        "Theta_T": t_t, "Theta_S": t_s,
        "Alpha": alpha, "Beta": beta, "Gamma": gamma,
        "Avg_TR_F1": round(np.mean(config_tr_f1), 4),
        "Avg_Cluster_ARI_All": round(np.mean(config_ari), 4),
        "Avg_Cluster_ARI_GT_Only": round(np.mean(config_ari_gt), 4)
    })

df = pd.DataFrame(results)
df.sort_values(by="Avg_Cluster_ARI_GT_Only", ascending=False, inplace=True)
df.to_csv(OUTPUT_CSV, index=False)
print("Saved massive GT evaluation results to CSV.")
