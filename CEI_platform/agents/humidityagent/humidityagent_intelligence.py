# data/agent4_capabilities.py

import json
from datetime import datetime, timedelta

def get_intelligence_data(data_log_path, agent_name, unit):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {"error": "No data available"}

        # Filter last 5 minutes of data
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [
            r["humidity"] for r in records
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return {"error": "No recent data in last 5 minutes"}

        return {
            "average_humidity": round(sum(recent) / len(recent), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "min_humidity": min(recent),
            "max_humidity": max(recent),
            "data_points_analyzed": len(recent),
            "unit": unit
        }

    except Exception as e:
        return {"error": str(e)}
