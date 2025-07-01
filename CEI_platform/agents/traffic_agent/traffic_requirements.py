from datetime import datetime, timedelta
from collections import Counter

def get_requirements_data(data_log_path, agent_name, duration=5, requirement="average_vehicle_count"):
    """
    Processes traffic data log file to calculate requested requirement
    over the last `duration` minutes.
    """
    import json, os

    if not os.path.exists(data_log_path):
        return {"error": "No data log found"}

    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)
    except json.JSONDecodeError:
        return {"error": "Invalid data log format"}

    cutoff = datetime.utcnow() - timedelta(minutes=duration)
    recent = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

    if not recent:
        return {"response": f"No recent data in last {duration} minutes"}

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
        return {"error": f"Unknown requirement: {requirement}"}

    return {
        "agent": agent_name,
        "requirement": requirement,
        "value": value,
        "unit": unit,
        "data_points_considered": len(recent)
    }
