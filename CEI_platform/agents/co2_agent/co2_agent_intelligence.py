import json
from datetime import datetime, timedelta
from collections import Counter

def get_intelligence_data(data_log_path, agent_name, unit):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {"error": "No data available"}

        # Filter records from the last 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {"error": "No recent data in last 5 minutes"}

        co2_values = [r["co2_level"] for r in recent]
        statuses = [r.get("co2_status", "Unknown") for r in recent]

        return {
            "average_co2": round(sum(co2_values) / len(co2_values), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "min_co2": min(co2_values),
            "max_co2": max(co2_values),
            "most_common_co2_status": Counter(statuses).most_common(1)[0][0],
            "data_points_analyzed": len(recent),
            "unit": unit
        }

    except Exception as e:
        return {"error": str(e)}
