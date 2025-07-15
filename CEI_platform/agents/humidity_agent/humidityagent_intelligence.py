# data/agent4_capabilities.py

# intelligence.py
import os
import json
from datetime import datetime, timedelta
from . import humidity_statistics as stats

def generate_and_save_intelligence(data_log_path, agent_name, port):
    try:
        if not os.path.exists(data_log_path):
            return {"error": "Data log not found"}

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {"error": "No data available"}

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {"error": "Nil"}

        latest = recent[-1]
        humidity_values = [r["humidity"] for r in recent if "humidity" in r]

        result = {
            "agent": agent_name,
            "capabilities": [
                {"parameter": "humidity", "unit": "%"}
            ],
            "data": {
                "humidity": {
                    "value": latest.get("humidity_status", "Unknown"),
                    "unit": "%",
                    "average_humidity": stats.calculate_average_humidity(humidity_values),
                    "max_humidity": stats.calculate_max_humidity(humidity_values),
                    "min_humidity": stats.calculate_min_humidity(humidity_values)
                }
            },
            "last_updated": datetime.utcnow().isoformat()
        }

        return result

    except Exception as e:
        return {"error": str(e)}

# Alias for compatibility
get_intelligence_data = generate_and_save_intelligence

# Optional test
if __name__ == "__main__":
    print(generate_and_save_intelligence("/data/humidity_agent_data_log.json", "humidity_agent", port=5003))
