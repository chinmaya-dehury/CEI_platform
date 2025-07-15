import os
import json
from datetime import datetime, timedelta
from . import traffic_statistics as stats

def generate_and_save_intelligence(data_log_path, agent_name, port):
    try:
        if not os.path.exists(data_log_path):
            return {"error": "Data log not found"}

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return { "No data available"}

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return { "Nil"}

        latest = recent[-1]
        vehicle_counts = [r["vehicle_count"] for r in recent if "vehicle_count" in r]

        result = {
            "agent": agent_name,
            "capabilities": [
                {"parameter": "traffic", "unit": "%"}
            ],
            "data": {
                "traffic": {
                    "value": latest.get("congestion_status", "Unknown"),
                    "unit": "%",
                    "average_vehicle_count": stats.calculate_average_vehicle_count(vehicle_counts),
                    "max_vehicle_count": stats.calculate_max_vehicle_count(vehicle_counts),
                    "min_vehicle_count": stats.calculate_min_vehicle_count(vehicle_counts)
                }
            },
            "last_updated": datetime.utcnow().isoformat()
        }

        return result

    except Exception as e:
        return {"error": str(e)}

# Alias for imports
get_intelligence_data = generate_and_save_intelligence

# Optional: test the function directly
if __name__ == "__main__":
    print(generate_and_save_intelligence("/agents/traffic_agent/traffic_agent_data_log.json", "traffic_agent", port="5000"))
