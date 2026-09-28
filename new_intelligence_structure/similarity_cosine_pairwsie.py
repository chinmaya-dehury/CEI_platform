import glob
import json
import os

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import MDS
from sklearn.metrics import davies_bouldin_score
from sklearn.metrics import pairwise_distances
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure'
OUT_DIR = os.path.join(BASE_DIR, 'similarity_results', 'cosine_experiment')
os.makedirs(OUT_DIR, exist_ok=True)

ALPHA_VALUES = np.arange(0.0, 1.01, 0.1)


json_files = glob.glob(os.path.join(BASE_DIR, '**', '*.json'), recursive=True)
json_files = [
    path for path in json_files
    if os.path.basename(path) not in {
        'intelligence_structure.json',
        'task_execution_clusters.json',
    }
]

intelligences = []
for path in sorted(json_files):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if 'metadata' in data:
            intelligences.append(data)
    except (OSError, json.JSONDecodeError):
        continue

labels = [item.get('metadata', {}).get('id', f'item_{index}')
          for index, item in enumerate(intelligences)]
text_corpus = []
tags_list = []

for item in intelligences:
    metadata = item.get('metadata', {})
    text_corpus.append(
        f"{metadata.get('name', '')}. {metadata.get('description', '')}. "
        f"Context: {metadata.get('context', '')}"
    )
    domain = metadata.get('domain', [])
    tags = metadata.get('tags', [])
    domain_values = domain if isinstance(domain, list) else [domain]
    tag_values = tags if isinstance(tags, list) else [tags]
    tags_list.append(domain_values + tag_values)

model = SentenceTransformer('all-mpnet-base-v2')
text_embeddings = model.encode(text_corpus, batch_size=32, show_progress_bar=False)

# cosine_similarity returns similarity directly: identical vectors are 1.0.
text_similarity = cosine_similarity(text_embeddings)

# Convert domain and tag values to one sentence per intelligence.
tag_sentences = [
    " ".join(str(value) for value in item_tags if str(value).strip())
    for item_tags in tags_list
]

# Encode domain/tag sentences into dense semantic vector space.
tag_embeddings = model.encode(
    tag_sentences,
    batch_size=32,
    show_progress_bar=False,
)
S_tags_semantic = 1.0 - pairwise_distances(tag_embeddings, metric='cosine')
S_tags_semantic = np.clip(S_tags_semantic, 0.0, 1.0)
np.fill_diagonal(S_tags_semantic, 1.0)

best_score = np.inf
best_alpha = None
best_beta = None
best_matrix = None
best_k = None

for alpha in ALPHA_VALUES:
    beta = 1.0 - alpha
    similarity = np.clip(
        alpha * text_similarity + beta * S_tags_semantic,
        0.0,
        1.0,
    )
    np.fill_diagonal(similarity, 1.0)
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
            best_score, best_alpha, best_beta = score, alpha, beta
            best_matrix, best_k = similarity.copy(), k

FEATURE_SIMILARITY = best_matrix
print(f'Best alpha={best_alpha:.1f}, beta={best_beta:.1f}, K={best_k}, DB={best_score:.4f}')

pd.DataFrame(
    FEATURE_SIMILARITY,
    index=labels,
    columns=labels,
).to_csv(os.path.join(OUT_DIR, 'similarity_matrix.csv'))

for name, matrix in {
    'text_cosine_similarity': text_similarity,
    'domain_tags_semantic_similarity': S_tags_semantic,
}.items():
    pd.DataFrame(matrix, index=labels, columns=labels).to_csv(
        os.path.join(OUT_DIR, f'{name}.csv')
    )

with open(os.path.join(OUT_DIR, 'index_mapping.json'), 'w', encoding='utf-8') as file:
    json.dump({str(index): label for index, label in enumerate(labels)}, file, indent=2)

print(f'Calculated text and domain/tag semantic similarity for {len(labels)} intelligences.')