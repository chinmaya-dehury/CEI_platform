import json
from itertools import combinations
import os
# --------------------------------------------------
# Configuration

# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTELLIGENCE_FILE = os.path.join(BASE_DIR, "intelligence_metadata.json")
THRESHOLD = 0.50

ALPHA = 0.5  # Task Similarity Weight
BETA = 0.3   # Context Similarity Weight
GAMMA = 0.2  # Domain Similarity Weight

# --------------------------------------------------
# Load Intelligence Metadata
# --------------------------------------------------

with open(INTELLIGENCE_FILE, "r") as f:
    intelligences = json.load(f)

# --------------------------------------------------
# Semantic Relationship Calculation
# --------------------------------------------------

def semantic_relationship(i1, i2):

    tasks1 = set(i1.get("tasks", []))
    tasks2 = set(i2.get("tasks", []))

    union_tasks = tasks1.union(tasks2)

    if len(union_tasks) == 0:
        task_similarity = 0
    else:
        task_similarity = len(tasks1.intersection(tasks2)) / len(union_tasks)

    context_similarity = ( 1 if i1.get("context") == i2.get("context") else 0 )

    domain_similarity = ( 1 if i1.get("domain") == i2.get("domain") else 0  )   

    sr = ( ALPHA * task_similarity + BETA * context_similarity + GAMMA * domain_similarity )

    return round(sr, 3)

# --------------------------------------------------
# Find Semantic Relationships
# --------------------------------------------------

print("\n==============================")
print("SEMANTIC RELATIONSHIPS")
print("==============================\n")

relationships = []

for i1, i2 in combinations(intelligences, 2):

    score = semantic_relationship(i1, i2)

    print(
        f"{i1['id']} ({i1['name']}) <--> "
        f"{i2['id']} ({i2['name']}) "
        f"SR = {score}"
    )

    if score >= THRESHOLD:
        relationships.append((i1["id"], i2["id"]))

# --------------------------------------------------
# Cluster Formation
# --------------------------------------------------

print("\n==============================")
print("CLUSTERS")
print("==============================\n")

clusters = []

visited = set()

for intel in intelligences:

    if intel["id"] in visited:
        continue

    cluster = {intel["id"]}

    for r in relationships:

        if intel["id"] in r:
            cluster.update(r)

    visited.update(cluster)

    clusters.append(cluster)

# --------------------------------------------------
# Print Clusters
# --------------------------------------------------

for idx, cluster in enumerate(clusters, start=1):

    print(f"Cluster-{idx}")

    for intel_id in cluster:

        intel_name = next(
            x["name"]
            for x in intelligences
            if x["id"] == intel_id
        )

        print(f"   {intel_id} -> {intel_name}")

    print()

print("==============================")
print("SUMMARY")
print("==============================")
print(f"Threshold : {THRESHOLD}")
print(f"Total Intelligences : {len(intelligences)}")
print(f"Total Clusters : {len(clusters)}")