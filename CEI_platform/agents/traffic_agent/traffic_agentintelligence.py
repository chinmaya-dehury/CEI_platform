import json
from datetime import datetime, timedelta
from collections import Counter

def get_intelligence_data(data_log_path, agent_name, unit):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {"error": "No data available"}

        # Last 5 minutes only
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {"error": f"No recent data in last 5 minutes"}

        vehicle_counts = [r["vehicle_count"] for r in recent]
        statuses = [r["congestion_status"] for r in recent]

        return {
            "average_vehicle_count": round(sum(vehicle_counts) / len(vehicle_counts), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "min_vehicle_count": min(vehicle_counts),
            "max_vehicle_count": max(vehicle_counts),
            "most_common_congestion_status": Counter(statuses).most_common(1)[0][0],
            "data_points_analyzed": len(recent)
        }

    except Exception as e:
        return {"error": str(e)}
