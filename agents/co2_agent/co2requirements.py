# data/requirements.py

import os
import json
import requests
from datetime import datetime, timedelta
from collections import Counter

SEARCH_SERVICE_URL = "http://localhost:5006/search"


def send_requirement_to_search(requirement_key):
    try:
        response = requests.get(f"{SEARCH_SERVICE_URL}?requirement={requirement_key}")
        if response.status_code == 200:
            return response.json(), 200
        else:
            return {"error": f"Search service returned {response.status_code}"}, response.status_code
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 500


def get_requirements_data(data_log_path, agent_name, unit, requirement="average_co2", duration=5):
    # Fallback logic (used only if search fails)
    if not os.path.exists(data_log_path):
        return {"error": "No data log found"}, 404

    with open(data_log_path, "r") as f:
        records = json.load(f)

    cutoff = datetime.utcnow() - timedelta(minutes=duration)
    recent_records = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

    if not recent_records:
        return {"response": f"No recent data in last {duration} minutes"}, 200

    co2_values = [r["co2_level"] for r in recent_records]

    if requirement == "average_co2":
        value = round(sum(co2_values) / len(co2_values), 2)
        result_unit = unit
    elif requirement == "min_co2":
        value = min(co2_values)
        result_unit = unit
    elif requirement == "max_co2":
        value = max(co2_values)
        result_unit = unit
    elif requirement == "co2_status":
        statuses = [r.get("co2_status", "Unknown") for r in recent_records]
        value = Counter(statuses).most_common(1)[0][0]
        result_unit = "status"
    else:
        return {"error": f"Unknown requirement: {requirement}"}, 400

    return {
        "agent": agent_name,
        "requirement": requirement,
        "value": value,
        "unit": result_unit,
        "data_points_considered": len(recent_records)
    }, 200


if __name__ == "__main__":
    requirement = "max_co2"  # Can change to "average_co2", "co2_status", etc.
    print(f"\n Sending requirement '{requirement}' to search service...")

    result, status = send_requirement_to_search(requirement)
    if status == 200 and isinstance(result, list):
        print("Matching intelligence values found:")
        for entry in result:
            print(f"  → Value: {entry['value']} | Agent ID: {entry['agent_id']} | URL: {entry['url']}")
    else:
        print(f" Search failed or not available: {result.get('error')}")
        print(" Using fallback logic locally...")

        # Local fallback execution
        # Update these values based on your agent setup
        fallback_data_path = "data/co2_agent_log.json"
        agent_name = "co2_agent_1"
        unit = "ppm"

        local_result, _ = get_requirements_data(fallback_data_path, agent_name, unit, requirement)
        print(" Fallback result:", local_result)
