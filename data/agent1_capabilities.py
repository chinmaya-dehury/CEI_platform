import json
import os

from datetime import datetime, timedelta

def get_capabilities_data(data_log_path, agent_name, unit):
    if not data_log_path or not agent_name or not unit:
        return {"error": "Missing parameters"}

    if not os.path.exists(data_log_path):
        return {"agent": agent_name, "capabilities": "No data available"}

    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r["congestion_level"] for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {"agent": agent_name, "capabilities": "No recent data in last 5 minutes"}

        return {
            "agent": agent_name,
            "capabilities": {
                "average_congestion": round(sum(recent) / len(recent), 2),
                "min_congestion": min(recent),
                "max_congestion": max(recent),
                "unit": unit,
                "data_points_considered": len(recent)
            }
        }
    except Exception as e:
        return {"error": str(e)}
