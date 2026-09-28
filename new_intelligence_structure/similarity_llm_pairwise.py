import os
import glob
import json
import time
import requests
import numpy as np
from dotenv import load_dotenv
import re

# --- Configuration ---
load_dotenv(override=True)
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:8b')
BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure'
OUT_DIR = os.path.join(BASE_DIR, 'similarity_results', 'llm_experiment')
os.makedirs(OUT_DIR, exist_ok=True)

BATCH_SIZE = 3  # Compare 1 reference item against 3 target items at once

PROMPT_TEMPLATE = """Evaluate how strongly the Reference Item is related or complementary to each Target Item for understanding a common situation, context, or task.

Compare the Reference Item independently with each Target Item. Give a score from 0.00 to 1.00. High scores are valid for direct similarity OR useful joint information for the same situation/task. Do not rely on shared words alone.

Reference Item:
{reference_item}

Target Items:
{target_items}

Consider:
1. Semantic relationship: Similar meaning, purpose, entities, measurements, or operations.
2. Domain relationship: Same application domain, system, process, or operational area.
3. Context relationship: Same environment, users, conditions, event, decision, or task.
4. Tag relationship: Shared concepts, assets, signals, goals, or categories. Tags are supporting evidence only.
5. Complementarity: Whether both items together provide useful information for understanding, monitoring, diagnosing, predicting, or acting on a common situation/task.

Score:
- 0.00-0.19 = No meaningful relationship
- 0.20-0.39 = Weak relationship
- 0.40-0.59 = Moderate relationship
- 0.60-0.79 = Strong relationship
- 0.80-1.00 = Very strong relationship

Rules:
- Similarity and complementarity both count.
- Shared domain or tags alone cannot justify a high score.
- Penalize contradictions in domain, context, purpose, or entities.
- Use the full score range and at most two decimal places.
- Do not infer information not present in the items.

Return ONLY a JSON object mapping each EXACT target ID to its float score. Include exactly one key per target ID and no explanation or markdown.

Example:
{{
  "AGR_02_225ce": 0.75,
  "AGR_03_3834d": 0.20
}}
"""

def extract_relevant_fields(intel_data):
    """Extracts only the fields permitted for LLM evaluation."""
    meta = intel_data.get("metadata", {})
    items = intel_data.get("intelligence_items", [{}])
    item = items[0] if items else {}
    
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "description": meta.get("description"),
        "domain": meta.get("domain"),
        "context": meta.get("context"),
        "tags": meta.get("tags"),
        "intelligence": item.get("intelligence")
    }


def parse_llm_scores(raw_text, target_ids):
    # Clean standard markdown code fences if generated
    clean_text = re.sub(r'```(?:json)?\s*|\s*```', '', raw_text, flags=re.IGNORECASE).strip()
    validated_scores = {}
    
    try:
        data = json.loads(clean_text)
    except Exception:
        # Fallback regex extraction if model adds surrounding prose
        data = {}
        for tid in target_ids:
            match = re.search(rf'"{re.escape(tid)}"\s*:\s*(0(?:\.\d+)?|1(?:\.0+)?)', raw_text)
            if match:
                data[tid] = float(match.group(1))

    for tid in target_ids:
        score = None
        if tid in data:
            score = data[tid]
        else:
            # Fuzzy match in case model modifies ID formatting slightly
            for key, val in data.items():
                if key in tid or tid in key:
                    score = val
                    break
        
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            numeric_score = -1.0

        if 0.0 <= numeric_score <= 1.0:
            validated_scores[tid] = round(numeric_score, 2)
        else:
            # Print raw response for debugging instead of silently setting to 0
            print(f"[Warning] Could not extract valid score for target '{tid}'")
            print(f"Raw Model Output was:\n{raw_text}\n")
            validated_scores[tid] = 0.0

    return validated_scores

def evaluate_batch_with_llm(ref_intel, target_intels):
    ref_data = extract_relevant_fields(ref_intel)
    targets_data = [extract_relevant_fields(t) for t in target_intels]
    
    prompt = PROMPT_TEMPLATE.format(
        reference_item=json.dumps(ref_data, indent=2),
        target_items=json.dumps(targets_data, indent=2)
    )
    
    host = OLLAMA_HOST if OLLAMA_HOST.startswith('http') else f"http://{OLLAMA_HOST}"
    url = f"{host}/api/generate"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096  # Ensure context window is explicitly set
        }
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=90)
            resp.raise_for_status()
            
            raw_text = resp.json().get('response', '').strip()
            
            if not raw_text:
                print(f"Warning: Empty response body on attempt {attempt+1}")
                continue

            target_ids = [target['id'] for target in targets_data]
            return parse_llm_scores(raw_text, target_ids)
            
        except requests.exceptions.RequestException as http_err:
            print(f"HTTP Error on attempt {attempt+1}: {http_err}")
        except json.JSONDecodeError:
            print(f"Raw response was non-JSON: {resp.text if 'resp' in locals() else 'None'}")
        except Exception as e:
            print(f"Error on attempt {attempt+1}: {e}")
            
        time.sleep(2)
            
    return {t['id']: 0.0 for t in targets_data}


def main():
    print(f"Targeting Ollama at {OLLAMA_HOST} with model {OLLAMA_MODEL}")
    
    # Load all intelligences
    files = glob.glob(os.path.join(BASE_DIR, '**', '*.json'), recursive=True)
    files = sorted([f for f in files if os.path.basename(f) not in ['intelligence_structure.json', 'task_execution_clusters.json']])
    
    data_list = []
    for f in files:
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
            if 'metadata' in data:
                data_list.append(data)
                
    n = len(data_list)
    total_pairs = n * (n - 1) // 2
    print(f"Loaded {n} intelligences. Total comparisons required: {total_pairs}")
    
    llm_sim_matrix = np.zeros((n, n))
    np.fill_diagonal(llm_sim_matrix, 1.0)
    
    detailed_scores = []
    processed_count = 0
    
    for i in range(n):
        ref_item = data_list[i]
        ref_id = ref_item['metadata']['id']
        
        # Gather all remaining target items for upper triangle matrix
        targets_indices = list(range(i + 1, n))
        
        # Batch remaining targets into groups of 3
        for chunk_idx in range(0, len(targets_indices), BATCH_SIZE):
            chunk_indices = targets_indices[chunk_idx:chunk_idx + BATCH_SIZE]
            target_items = [data_list[j] for j in chunk_indices]
            
            target_ids = [t['metadata']['id'] for t in target_items]
            print(f"Evaluating {ref_id} vs targets: {target_ids}...")
            
            scores = evaluate_batch_with_llm(ref_item, target_items)
            
            for j, target_item in zip(chunk_indices, target_items):
                t_id = target_item['metadata']['id']
                score = scores.get(t_id, 0.0)
                
                # Symmetrical matrix update
                llm_sim_matrix[i, j] = score
                llm_sim_matrix[j, i] = score
                
                detailed_scores.append({
                    "intelligence_1": ref_id,
                    "intelligence_2": t_id,
                    "score": score,
                    "model": OLLAMA_MODEL
                })
                
            processed_count += len(chunk_indices)
            
            # Periodic save
            if processed_count % 12 == 0:
                np.save(os.path.join(OUT_DIR, 'llm_sim_matrix_partial.npy'), llm_sim_matrix)
                with open(os.path.join(OUT_DIR, 'llm_reasons_partial.json'), 'w', encoding='utf-8') as f:
                    json.dump(detailed_scores, f, indent=2)

    # Final Save
    np.save(os.path.join(OUT_DIR, 'llm_sim_matrix.npy'), llm_sim_matrix)
    with open(os.path.join(OUT_DIR, 'llm_reasons.json'), 'w', encoding='utf-8') as f:
        json.dump(detailed_scores, f, indent=2)
        
    print("LLM Batch Similarity Computation Complete!")

if __name__ == "__main__":
    main()