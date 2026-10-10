import glob
import json
import os

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import MDS
from sklearn.metrics import davies_bouldin_score
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure'
OUT_DIR = os.path.join(BASE_DIR, 'similarity_results', 'single_text_experiment')
os.makedirs(OUT_DIR, exist_ok=True)

# 1. Load Data & Combine Everything into One Text String per Intelligence
json_files = glob.glob(os.path.join(BASE_DIR, '**', '*.json'), recursive=True)
json_files = [
    path for path in json_files
    if os.path.basename(path) not in {'intelligence_structure.json', 'task_execution_clusters.json'}
]

print("started")

intelligences = []
for path in sorted(json_files):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if 'metadata' in data:
            intelligences.append(data)
    except (OSError, json.JSONDecodeError):
        continue

labels = [item.get('metadata', {}).get('id', f'item_{index}') for index, item in enumerate(intelligences)]

combined_corpus = []

for item in intelligences:
    metadata = item.get('metadata', {})
    
    name = metadata.get('name', '')
    description = metadata.get('description', '')
    context = metadata.get('context', '')
    
    domain = metadata.get('domain', [])
    tags = metadata.get('tags', [])
    domain_list = domain if isinstance(domain, list) else [domain]
    tags_list = tags if isinstance(tags, list) else [tags]
    
    domain_str = " ".join(str(v) for v in domain_list if str(v).strip())
    tags_str = " ".join(str(v) for v in tags_list if str(v).strip())
    
    # Single merged string combining text, domain, and tags
    full_text = f"{name} {description} {context} {domain_str} {tags_str}"
    combined_corpus.append(full_text)

# --- REQUIREMENT 1: Print the complete text for one intelligence ---
print("=" * 80)
print(f"COMPLETE TEXT FOR FIRST INTELLIGENCE ({labels[0]}):")
print(combined_corpus[0])
print("=" * 80)

# 2. Compute Single Embedding Space
model = SentenceTransformer('all-mpnet-base-v2')
#model = SentenceTransformer('all-MiniLM-L6-v2') 
text_embeddings = model.encode(combined_corpus, batch_size=32, show_progress_bar=False)

# --- REQUIREMENT 2: Print embedding result for one intelligence ---
print("\n" + "=" * 80)
print(f"EMBEDDING RESULT FOR FIRST INTELLIGENCE ({labels[0]}):")
print(f"Shape: {text_embeddings[0].shape}")
print(f"First 10 values: {text_embeddings[0][:10]}")
print("=" * 80 + "\n")

# 3. Direct Cosine Similarity (No weights needed)
similarity = cosine_similarity(text_embeddings)
similarity = np.clip(similarity, 0.0, 1.0)
np.fill_diagonal(similarity, 1.0)

# 4. Clustering Optimization over K
best_score = np.inf
best_matrix = similarity.copy()
best_k = None

distance = 1.0 - similarity

coordinates = MDS(
    n_components=min(10, len(labels) - 1),
    metric='precomputed',
    init='random',
    random_state=42,
).fit_transform(distance)

for k in range(2, min(11, len(labels))):
    cluster_labels = AgglomerativeClustering(n_clusters=k).fit_predict(coordinates)
    score = davies_bouldin_score(coordinates, cluster_labels)
    
    if score < best_score:
        best_score = score
        best_k = k

FEATURE_SIMILARITY = best_matrix
print(f'Best K={best_k}, DB Score={best_score:.4f}')

# 5. Save Outputs
pd.DataFrame(FEATURE_SIMILARITY, index=labels, columns=labels).to_csv(
    os.path.join(OUT_DIR, 'similarity_matrix.csv')
)

with open(os.path.join(OUT_DIR, 'index_mapping.json'), 'w', encoding='utf-8') as file:
    json.dump({str(index): label for index, label in enumerate(labels)}, file, indent=2)

print(f'Calculated similarity for {len(labels)} items using single merged embeddings.')