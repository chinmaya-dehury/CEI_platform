from datetime import datetime, timedelta
import json
import os

def get_capabilities_data(log_path, agent_name, unit):
    if not os.path.exists(log_path):
        return {"agent": agent_name, "capabilities": "No data available"}

    try:
        with open(log_path, "r") as f:
            records = json.load(f)

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r["noise_level"] for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {"agent": agent_name, "capabilities": "No recent data in last 5 minutes"}

        return {
            "agent": agent_name,
            "capabilities": {
                "average_noise_level": round(sum(recent) / len(recent), 2),
                "min_noise_level": min(recent),
                "max_noise_level": max(recent),
                "unit": unit,
                "data_points_considered": len(recent)
            }
        }

    except Exception as e:
        return {"error": str(e)}
