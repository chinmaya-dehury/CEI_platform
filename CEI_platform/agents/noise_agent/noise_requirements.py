import os
import json
import requests
from datetime import datetime, timedelta
from flask import request

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


def get_requirements_data(data_log_path, agent_name, unit, requirement="average_noise", duration=5):
    # Override if called via POST with payload
    if request.method == 'POST':
        req_data = request.get_json()
        if req_data:
            requirement = req_data.get("requirement", requirement)
            duration = int(req_data.get("duration_minutes", duration))

    # Try global intelligence first
    result, status = send_requirement_to_search(requirement)
    if status == 200 and isinstance(result, list):
        return {
            "source": "search_service",
            "results": result
        }, 200

    # Fallback to local noise analysis
    if not os.path.exists(data_log_path):
        return {"error": "No data log found"}, 404

    with open(data_log_path, "r") as f:
        records = json.load(f)

    cutoff = datetime.utcnow() - timedelta(minutes=duration)
    recent = [
        r["noise_level"] for r in records
        if datetime.fromisoformat(r["timestamp"]) > cutoff
    ]

    if not recent:
        return {"response": f"No recent noise data in last {duration} minutes"}, 200

    if requirement == "average_noise":
        value = round(sum(recent) / len(recent), 2)
    elif requirement == "min_noise":
        value = min(recent)
    elif requirement == "max_noise":
        value = max(recent)
    else:
        return {"error": f"Unknown requirement: {requirement}"}, 400

    return {
        "source": "local_agent",
        "agent": agent_name,
        "requirement": requirement,
        "value": value,
        "unit": unit,
        "data_points_considered": len(recent)
    }, 200
