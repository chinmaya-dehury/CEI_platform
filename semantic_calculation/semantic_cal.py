import os
import json
from itertools import combinations
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------
# Paths & Configuration
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTELLIGENCE_FILE = os.path.join(BASE_DIR, "intelligence_metadata.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "task_execution_clusters.json")

# Model Setup
print("Initializing semantic embedding engine...")
#model = SentenceTransformer("all-MiniLM-L6-v2")
model = SentenceTransformer("all-mpnet-base-v2")  # More accurate but heavier model

# Decision Thresholds
# Justification (Sensitivity Analysis): 
# THETA_1 (0.80) acts as a strict precision filter. Lower values (e.g., 0.60) create overly large, inefficient clusters, 
# while higher values (0.90) isolate agents too aggressively, hurting collaboration.
# THETA_2 (0.45) is moderate to maintain high recall. Higher values restrict participating agents, reducing adaptability.
THETA_1 = 0.80  # SR Threshold
THETA_2 = 0.45  # TR Threshold (How relevant an agent must be to participate - moderate recall)

# SR Weight Configuration: alpha + beta + gamma = 1
# Justification: Task similarity (alpha) is prioritized as functional alignment is most critical for execution.
# Context (beta) provides situational relevance, while Domain (gamma) is given the lowest weight because 
# functional tasks (e.g., thermal sensing) are often cross-domain (e.g., SmartBuilding to Transportation).
ALPHA = 0.5   # Task Similarity Weight
BETA = 0.3    # Context Similarity Weight
GAMMA = 0.2   # Domain Similarity Weight

# Load Data
if not os.path.exists(INTELLIGENCE_FILE):
    raise FileNotFoundError(f"Missing metadata file at: {INTELLIGENCE_FILE}")

with open(INTELLIGENCE_FILE, "r") as f:
    intelligences = json.load(f)

# --------------------------------------------------
# Helper Embedding Functions
# --------------------------------------------------
def get_tasks_embedding(tasks_list):
    """Combines task names and descriptions into an average vector profile."""
    if not tasks_list:
        return np.zeros((384,))
    task_texts = []
    for t in tasks_list:
        if isinstance(t, dict):
            task_texts.append(f"Task: {t.get('name', '')}. Description: {t.get('description', '')}")
        else:
            task_texts.append(str(t))
    return np.mean(model.encode(task_texts), axis=0)

# Pre-calculate internal intelligence representations
for intel in intelligences:
    intel["_context_vector"] = model.encode(intel.get("context", ""))
    intel["_domain_vector"] = model.encode(intel.get("domain", ""))
    intel["_tasks_vector"] = get_tasks_embedding(intel.get("tasks", []))
    # Full identity text for Task Relevance matching
    intel_tasks_str = ", ".join([str(t) for t in intel.get("tasks", [])])
    intel["_identity_text"] = f"Intelligence: {intel['name']}. Domain: {intel['domain']}. Context: {intel['context']}. Description: {intel.get('description', '')}. Tasks: {intel_tasks_str}."

def calculate_sr(i1, i2):
    """Calculates the pure Semantic Relationship between two intelligences."""
    v_task1, v_task2 = i1["_tasks_vector"].reshape(1, -1), i2["_tasks_vector"].reshape(1, -1)
    v_context1, v_context2 = i1["_context_vector"].reshape(1, -1), i2["_context_vector"].reshape(1, -1)
    v_domain1, v_domain2 = i1["_domain_vector"].reshape(1, -1), i2["_domain_vector"].reshape(1, -1)

    task_sim = cosine_similarity(v_task1, v_task2)[0][0]
    context_sim = cosine_similarity(v_context1, v_context2)[0][0]
    domain_sim = cosine_similarity(v_domain1, v_domain2)[0][0]

    if np.all(v_task1 == 0) or np.all(v_task2 == 0): task_sim = 0

    sr = (ALPHA * task_sim) + (BETA * context_sim) + (GAMMA * domain_sim)
    return round(float(sr), 3)

# --------------------------------------------------
# Execution Flow
# --------------------------------------------------

# Step 1: User Inputs a Task
import sys
print("\n==================================================")
if len(sys.argv) > 1:
    user_task = sys.argv[1].strip()
    print(f"Using provided task: '{user_task}'")
else:
    user_task = input("Enter Task Description: ").strip()
    if not user_task:
        user_task = "Detect fire incidents in forest areas and alert local emergency services."
        print(f"Using default task: '{user_task}'")
print("==================================================")

task_vector = model.encode(user_task).reshape(1, -1)

# Step 2: Score all Intelligences via Task Relevance (TR)
print("\n[STEP 2] SCORING & FILTERING INTELLIGENCES (TR)")
print("-" * 70)

survivors = []
eliminated_logs = []

for intel in intelligences:
    intel_vector = model.encode(intel["_identity_text"]).reshape(1, -1)
    tr_score = round(float(cosine_similarity(task_vector, intel_vector)[0][0]), 3)
    intel["_tr_score"] = tr_score
    
    if tr_score >= THETA_2:
        print(f"✅ PASS | {intel['id']} ({intel['name']}) | TR Score: {tr_score:.3f}")
        survivors.append(intel)
    else:
        print(f"❌ DROP | {intel['id']} ({intel['name']}) | TR Score: {tr_score:.3f}")
        eliminated_logs.append({"id": intel["id"], "name": intel["name"], "tr_score": tr_score})

# Step 3: Group the top-scoring performers using Semantic Relationship (SR)
print("\n[STEP 3] EVALUATING SURVIVOR RELATIONSHIPS (SR)")
print("-" * 70)

relationships = []
for i1, i2 in combinations(survivors, 2):
    sr_score = calculate_sr(i1, i2)
    print(f"Pair: {i1['id']} <--> {i2['id']} | SR Score: {sr_score:.3f}")
    if sr_score >= THETA_1:
        relationships.append((i1["id"], i2["id"]))

# Clustering logic applied exclusively to qualified survivors
clusters = []
visited = set()

for intel in survivors:
    intel_id = intel["id"]
    if intel_id in visited:
        continue

    cluster = {intel_id}
    while True:
        previous_size = len(cluster)
        for r in relationships:
            if r[0] in cluster or r[1] in cluster:
                cluster.update(r)
        if len(cluster) == previous_size:
            break

    visited.update(cluster)
    clusters.append(cluster)

# --------------------------------------------------
# CR Selection Logic (Algorithm 2)
# --------------------------------------------------
print("\n[STEP 4] CALCULATING CLUSTER RELEVANCE (CR)")
print("-" * 70)

id_to_intel = {x["id"]: x for x in survivors}
cluster_metrics = []

for idx, cluster in enumerate(clusters, start=1):
    tr_scores = [id_to_intel[agent_id]["_tr_score"] for agent_id in cluster]
    cr_score = sum(tr_scores) / len(cluster)
    max_tr = max(tr_scores)
    cluster_metrics.append({
        "cluster": cluster,
        "cluster_id": f"Cluster-{idx}",
        "cr_score": cr_score,
        "size": len(cluster),
        "max_tr": max_tr
    })
    print(f"Cluster-{idx} | Size: {len(cluster)} | CR Score: {cr_score:.3f} | Max TR: {max_tr:.3f}")

# Sort by CR Score (desc), then Size (desc), then Max TR (desc)
cluster_metrics.sort(key=lambda x: (x["cr_score"], x["size"], x["max_tr"]), reverse=True)
best_cluster = cluster_metrics[0]

print(f"\n=> SELECTED EXECUTING CLUSTER (C*): {best_cluster['cluster_id']} (CR: {best_cluster['cr_score']:.3f})")

# --------------------------------------------------
# Terminal Display Results
# --------------------------------------------------
id_to_name = {x["id"]: x["name"] for x in intelligences}

print("\n==============================")
print("FINAL COLLABORATION CLUSTERS")
print("==============================\n")

json_clusters_output = []

for idx, cluster in enumerate(clusters, start=1):
    print(f"Cluster-{idx} (Collaboration Group):")
    cluster_agents = []
    
    for intel_id in sorted(list(cluster)):
        print(f" {intel_id} -> {id_to_name[intel_id]}")
        cluster_agents.append({
            "id": intel_id, 
            "name": id_to_name[intel_id],
            "tr_score": id_to_intel[intel_id]["_tr_score"]
        })
        
    print()
    json_clusters_output.append({
        "cluster_id": f"Cluster-{idx}",
        "size": len(cluster),
        "agents": cluster_agents
    })

print("==============================")
print("RUN SUMMARY")
print("==============================")
print(f"Total Evaluated : {len(intelligences)}")
print(f"Total Active    : {len(survivors)}")
print(f"Total Eliminated: {len(eliminated_logs)}")
print(f"Total Groups    : {len(clusters)}")

# --------------------------------------------------
# Save Export Artifact
# --------------------------------------------------
export_data = {
    "target_task": user_task,
    "thresholds": {"sr_theta_1": THETA_1, "tr_theta_2": THETA_2},
    "summary": {
        "total_evaluated": len(intelligences),
        "total_active": len(survivors),
        "total_eliminated": len(eliminated_logs),
        "total_clusters": len(clusters)
    },
    "clusters": json_clusters_output,
    "selected_executing_cluster": {
        "cluster_id": best_cluster["cluster_id"],
        "cr_score": best_cluster["cr_score"],
        "size": best_cluster["size"],
        "max_tr": best_cluster["max_tr"]
    },
    "eliminated": eliminated_logs
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(export_data, f, indent=2)

print(f"\n💾 Execution results securely written to JSON at:\n👉 {OUTPUT_FILE}\n")