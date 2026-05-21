import os
import json
import requests
from datetime import datetime, timedelta
from flask import request
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

def get_requirements_data(data_log_path, agent_name, unit=None, requirement="average_vehicle_count", duration=5):
    # Allow override via POST
    if request.method == 'POST':
        req_data = request.get_json()
        if req_data:
            requirement = req_data.get("requirement", requirement)
            duration = int(req_data.get("duration_minutes", duration))

    # Try global intelligence
    result, status = send_requirement_to_search(requirement)
    if status == 200 and isinstance(result, list):
        return {
            "source": "search_service",
            "results": result
        }, 200

    # Fallback: Local traffic analysis
    if not os.path.exists(data_log_path):
        return {"error": "No data log found"}, 404

    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)
    except json.JSONDecodeError:
        return {"error": "Invalid data log format"}, 500

    cutoff = datetime.utcnow() - timedelta(minutes=duration)
    recent = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

    if not recent:
        return {"response": f"No recent data in last {duration} minutes"}, 200

    # Compute based on requirement
    if requirement == "average_vehicle_count":
        value = round(sum(r["vehicle_count"] for r in recent) / len(recent), 2)
        unit = "vehicles"
    elif requirement == "min_vehicle_count":
        value = min(r["vehicle_count"] for r in recent)
        unit = "vehicles"
    elif requirement == "max_vehicle_count":
        value = max(r["vehicle_count"] for r in recent)
        unit = "vehicles"
    elif requirement == "congestion_status":
        statuses = [r["congestion_status"] for r in recent]
        value = Counter(statuses).most_common(1)[0][0]
        unit = "status"
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
