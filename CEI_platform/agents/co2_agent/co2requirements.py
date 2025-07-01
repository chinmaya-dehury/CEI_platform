# data/requirements.py

import os
import json
from datetime import datetime, timedelta
from collections import Counter

def get_requirements_data(data_log_path, agent_name, unit, requirement="average_co2", duration=5):
    
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
