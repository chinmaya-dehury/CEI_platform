import os
import json
import time
import requests
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')

# Configuration
DOMAINS = [
    'Transportation', 'Agriculture', 'Manufacturing', 'Healthcare', 
    'Environment', 'Energy', 'Smart Building', 'Disaster Management'
]
NUM_INTELLIGENCES = 2
PROMPT_FILE = 'intelligence_conversion.md'
OUTPUT_BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure'

# Read prompt template
with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
    prompt_template = f.read()

def generate_intelligence(domain, index):
    """Call Ollama API to generate intelligence JSON"""
    concept = f"A highly specialized edge node sensor or AI agent for {domain} (Variant {index+1})"
    prompt = prompt_template.replace("{{DOMAIN}}", domain).replace("{{CONCEPT}}", concept)
    
    host = OLLAMA_HOST if OLLAMA_HOST.startswith('http') else f"http://{OLLAMA_HOST}"
    url = f"{host}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        response_text = data.get('response', '{}')
        
        # Ensure it's parseable JSON
        parsed_json = json.loads(response_text)
        return parsed_json
    except Exception as e:
        print(f"Error generating for {domain} #{index+1}: {e}")
        return None

def main():
    print(f"Starting Generation. Target: {NUM_INTELLIGENCES} agents per domain.")
    print(f"Using Ollama Model: {OLLAMA_MODEL} at {OLLAMA_HOST}")
    
    for domain in DOMAINS:
        domain_dir = os.path.join(OUTPUT_BASE_DIR, domain.replace(' ', '_'))
        os.makedirs(domain_dir, exist_ok=True)
        print(f"\n--- Generating for Domain: {domain} ---")
        
        success_count = 0
        attempts = 0
        while success_count < NUM_INTELLIGENCES and attempts < NUM_INTELLIGENCES * 2:
            print(f"  Attempt {attempts+1} to generate agent {success_count+1}...")
            intel_json = generate_intelligence(domain, success_count)
            
            if intel_json:
                # Force ID to be unique
                intel_id = f"{domain.replace(' ', '')[:3].upper()}_{uuid.uuid4().hex[:6].upper()}"
                if 'metadata' in intel_json:
                    intel_json['metadata']['id'] = intel_id
                    
                file_path = os.path.join(domain_dir, f"{intel_id}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(intel_json, f, indent=2)
                print(f"    -> Saved {file_path}")
                success_count += 1
            else:
                print("    -> Failed or invalid JSON, retrying...")
                
            attempts += 1
            time.sleep(1) # Small delay to avoid overloading
            
    print("\nGeneration Complete!")

if __name__ == "__main__":
    main()
