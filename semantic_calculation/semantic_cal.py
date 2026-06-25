import json
from itertools import combinations
import numpy as np
import os
# We use sentence-transformers to easily get semantic vectors
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Initialize a lightweight semantic text embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTELLIGENCE_FILE = os.path.join(BASE_DIR, "intelligence_metadata.json")
THRESHOLD = 0.60

ALPHA = 0.5   # Task Semantic Weight
BETA = 0.3    # Context Semantic Weight
GAMMA = 0.2   # Domain Semantic Weight

# Load Data
with open(INTELLIGENCE_FILE, "r") as f:
    intelligences = json.load(f)

# --------------------------------------------------
# Helper: Get Average Embedding for Tasks
# --------------------------------------------------
def get_tasks_embedding(tasks_list):
    """
    Combines task names and descriptions, encodes them, 
    and returns an average semantic vector for all tasks.
    """
    if not tasks_list:
        return np.zeros((384,)) # Model output size for MiniLM
    
    task_texts = []
    for t in tasks_list:
        # Combine name and description for rich semantic meaning
        combined_text = f"Task: {t.get('name', '')}. Description: {t.get('description', '')}"
        task_texts.append(combined_text)
        
    embeddings = model.encode(task_texts)
    return np.mean(embeddings, axis=0) # Average vector representing overall task profile

# Pre-calculate embeddings for performance
for intel in intelligences:
    intel["_context_vector"] = model.encode(intel.get("context", ""))
    intel["_domain_vector"] = model.encode(intel.get("domain", ""))
    intel["_tasks_vector"] = get_tasks_embedding(intel.get("tasks", []))

# --------------------------------------------------
# Semantic Relationship Calculation (Vector Version)
# --------------------------------------------------
def calculate_semantic_relationship(i1, i2):
    # Reshape vectors for sklearn's cosine_similarity function
    v_task1, v_task2 = i1["_tasks_vector"].reshape(1, -1), i2["_tasks_vector"].reshape(1, -1)
    v_context1, v_context2 = i1["_context_vector"].reshape(1, -1), i2["_context_vector"].reshape(1, -1)
    v_domain1, v_domain2 = i1["_domain_vector"].reshape(1, -1), i2["_domain_vector"].reshape(1, -1)

    # Calculate individual cosine similarities
    task_sim = cosine_similarity(v_task1, v_task2)[0][0]
    context_sim = cosine_similarity(v_context1, v_context2)[0][0]
    domain_sim = cosine_similarity(v_domain1, v_domain2)[0][0]

    # Handle cases where vectors might be empty/zero
    if np.all(v_task1 == 0) or np.all(v_task2 == 0): task_sim = 0

    # Weighted Semantic Relationship Score
    sr = (ALPHA * task_sim) + (BETA * context_sim) + (GAMMA * domain_sim)
    return round(float(sr), 3)

# --------------------------------------------------
# Find Relationships & Cluster (Same as your original logic)
# --------------------------------------------------
relationships = []
for i1, i2 in combinations(intelligences, 2):
    score = calculate_semantic_relationship(i1, i2)
    print(f"{i1['name']} <--> {i2['name']} | Semantic Score = {score}")
    
    if score >= THRESHOLD:
        relationships.append((i1["id"], i2["id"]))

# --------------------------------------------------
# Cluster Formation (Graph Components Algorithm)
# --------------------------------------------------
print("\n==============================")
print("CLUSTERS")
print("==============================\n")

clusters = []
visited = set()

for intel in intelligences:
    intel_id = intel["id"]
    if intel_id in visited:
        continue

    # Initialize a new cluster container with the root item
    cluster = {intel_id}
    
    # Breadth-first / iterative grouping of all connected items
    # Loop continuously until no new items can be added to the current cluster
    while True:
        previous_size = len(cluster)
        
        for r in relationships:
            # If any element in the relationship pair matches our cluster, pull both in
            if r[0] in cluster or r[1] in cluster:
                cluster.update(r)
                
        # If the cluster stopped growing, we've extracted the entire linked group
        if len(cluster) == previous_size:
            break

    visited.update(cluster)
    clusters.append(cluster)

# --------------------------------------------------
# Print Clusters & Summary
# --------------------------------------------------
# Build a quick lookup dictionary for ID -> Name formatting
id_to_name = {x["id"]: x["name"] for x in intelligences}

for idx, cluster in enumerate(clusters, start=1):
    print(f"Cluster-{idx}")
    for intel_id in sorted(list(cluster)):
        print(f"   {intel_id} -> {id_to_name[intel_id]}")
    print()

print("==============================")
print("SUMMARY")
print("==============================")
print(f"Threshold           : {THRESHOLD}")
print(f"Total Intelligences : {len(intelligences)}")
print(f"Total Clusters      : {len(clusters)}")