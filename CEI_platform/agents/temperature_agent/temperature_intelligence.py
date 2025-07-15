import os
import json
from datetime import datetime, timedelta
from . import temperature_statistics as stats  # Make sure this file exists with avg/min/max functions

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
            return {"Nil"}

        latest = recent[-1]
        temps = [r["temperature"] for r in recent if "temperature" in r]

        result = {
            "agent": agent_name,
            "capabilities": [
                {"parameter": "temperature", "unit": unit}
            ],
            "data": {
                "temperature": {
                    "value": latest.get("temperature", "Unknown"),
                    "unit": unit,
                    "average": stats.calculate_average_temperature(temps),
                    "max": stats.calculate_max_temperature(temps),
                    "min": stats.calculate_min_temperature(temps)
                }
            },
            "last_updated": datetime.utcnow().isoformat()
        }

        return result

    except Exception as e:
        return {"error": str(e)}

# Alias
get_intelligence_data = generate_and_save_intelligence

# Optional direct test
if __name__ == "__main__":
    print(generate_and_save_intelligence("/data/temperature_agent_data_log.json", "temperature_agent", unit="°C", port="5004"))
