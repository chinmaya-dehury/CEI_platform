import os
import json
from datetime import datetime, timedelta
from collections import Counter

def get_capabilities_data(data_log_path, agent_name, unit):
    if not os.path.exists(data_log_path):
        return {"error": "Data log not found"}

    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        # Only consider last 5 minutes of data
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_data = [
            r for r in records
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent_data:
            return {"message": "No recent data in last 5 minutes"}

        # Extract values
        values = [r["temperature"] for r in recent_data]
        statuses = [r.get("temperature_status", "Unknown") for r in recent_data]

        return {
            "agent": agent_name,
            "data_points_analyzed": len(values),
            "average_temperature": round(sum(values) / len(values), 2),
            "min_temperature": min(values),
            "max_temperature": max(values),
            "unit": unit,
            "status_distribution": dict(Counter(statuses))
        }

    except Exception as e:
        return {"error": str(e)}
