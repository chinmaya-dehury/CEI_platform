import os
import json
from datetime import datetime, timedelta
from . import co2_agent_statistics as stats

def generate_and_save_intelligence(data_log_path, agent_name, unit, port):
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
            return { "Nil"}

        latest = recent[-1]
        co2_levels = [r["co2_level"] for r in recent if "co2_level" in r]

        result = {
            "agent": agent_name,
            "capabilities": [
                {"parameter": "co2", "unit": unit}
            ],
            "data": {
                "co2": {
                    "value": latest.get("co2_status", "Unknown"),
                    "unit": unit,
                    "average": stats.calculate_average(co2_levels),
                    "max": stats.calculate_max(co2_levels),
                    "min": stats.calculate_min(co2_levels)
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
    print(generate_and_save_intelligence("/data/co2_agent_data_log.json", "co2_agent", "ppm", port=5001))
