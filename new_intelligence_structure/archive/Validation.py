import os
import json
import glob
from datetime import datetime

BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure'

def validate_datetime(dt_str):
    try:
        # Check ISO 8601 parsing loosely
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False

def validate_intelligence(data, file_path):
    errors = []
    
    # Check top-level keys
    if 'metadata' not in data:
        errors.append("Missing 'metadata' object")
    if 'intelligence_items' not in data:
        errors.append("Missing 'intelligence_items' array")
        
    if not errors:
        meta = data['metadata']
        # Check required metadata fields
        required_meta = ['id', 'name', 'version', 'agent', 'domain', 'source', 'status', 'update_mode']
        for req in required_meta:
            if req not in meta:
                errors.append(f"metadata missing required field: {req}")
                
        # Validate specific constraints
        if 'agent' in meta:
            if 'id' not in meta['agent']: errors.append("metadata.agent missing 'id'")
            if 'type' not in meta['agent']: errors.append("metadata.agent missing 'type'")
            elif meta['agent']['type'] not in ['fixed_location', 'mobile']:
                errors.append(f"Invalid agent type: {meta['agent']['type']}")
                
        if 'status' in meta and meta['status'] not in ['online', 'offline']:
            errors.append(f"Invalid status: {meta['status']}")
            
        if 'update_mode' in meta:
            valid_modes = ['periodic', 'event-driven', 'on-demand']
            if meta['update_mode'] not in valid_modes:
                errors.append(f"Invalid update_mode: {meta['update_mode']}")
            if meta['update_mode'] == 'periodic':
                if 'frequency' not in meta:
                    errors.append("update_mode is periodic but missing 'frequency'")
                else:
                    freq = meta['frequency']
                    if 'value' not in freq or 'unit' not in freq:
                        errors.append("frequency missing 'value' or 'unit'")
                    elif freq['unit'] not in ['sec', 'min', 'hr', 'mth', 'yr']:
                        errors.append(f"Invalid frequency unit: {freq['unit']}")
                        
        # Check intelligence_items
        items = data['intelligence_items']
        if not isinstance(items, list):
            errors.append("'intelligence_items' must be a list")
        else:
            for idx, item in enumerate(items):
                if 'intelligence' not in item:
                    errors.append(f"Item {idx} missing 'intelligence'")
                if 'generated_at' not in item:
                    errors.append(f"Item {idx} missing 'generated_at'")
                else:
                    if not validate_datetime(item['generated_at']):
                        errors.append(f"Item {idx} 'generated_at' is not valid ISO datetime")
                        
                if 'valid_until' in item:
                    if not validate_datetime(item['valid_until']):
                        errors.append(f"Item {idx} 'valid_until' is not valid ISO datetime")
                        
                if 'location' in item:
                    loc = item['location']
                    if 'latitude' not in loc or 'longitude' not in loc:
                        errors.append(f"Item {idx} location missing 'latitude' or 'longitude'")
                        
    return errors

def main():
    print("--- Starting Validation ---")
    json_files = glob.glob(os.path.join(BASE_DIR, '**', '*.json'), recursive=True)
    
    total_files = 0
    passed = 0
    failed = 0
    
    for file_path in json_files:
        # Skip the schema file itself
        if "intelligence_structure.json" in file_path:
            continue
            
        total_files += 1
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                errors = validate_intelligence(data, file_path)
                if errors:
                    failed += 1
                    print(f"❌ FAILED: {os.path.basename(file_path)}")
                    for err in errors:
                        print(f"    - {err}")
                else:
                    passed += 1
                    # print(f"✅ PASSED: {os.path.basename(file_path)}")
            except json.JSONDecodeError:
                failed += 1
                print(f"❌ INVALID JSON FORMAT: {os.path.basename(file_path)}")
                
    print("\n--- Validation Summary ---")
    print(f"Total Files Checked: {total_files}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()
