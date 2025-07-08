import os
import json
from datetime import datetime, timedelta
from collections import Counter

INTELLIGENCE_PATH = "/data/temperature_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit):
    try:
        if not os.path.exists(data_log_path):
            result = {"error": "Data log not found"}
        else:
            with open(data_log_path, "r") as f:
                records = json.load(f)

            # Only consider last 5 minutes of data
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            recent_data = [
                r for r in records
                if datetime.fromisoformat(r["timestamp"]) > cutoff
            ]

            if not recent_data:
                result = {"message": "No recent data in last 5 minutes"}
            else:
                values = [r["temperature"] for r in recent_data]
                statuses = [r.get("temperature_status", "Unknown") for r in recent_data]

                result = {
                    "agent": agent_name,
                    "data_points_analyzed": len(values),
                    "average_temperature": round(sum(values) / len(values), 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "min_temperature": min(values),
                    "max_temperature": max(values),
                    "unit": unit,
                    "status_distribution": dict(Counter(statuses))
                }
        # Save to JSON file
        os.makedirs(os.path.dirname(INTELLIGENCE_PATH), exist_ok=True)
        with open(INTELLIGENCE_PATH, "w") as out:
            json.dump(result, out, indent=2)
        return result

    except Exception as e:
        error = {"error": str(e)}
        try:
            os.makedirs(os.path.dirname(INTELLIGENCE_PATH), exist_ok=True)
            with open(INTELLIGENCE_PATH, "w") as out:
                json.dump(error, out, indent=2)
        except Exception:
            pass
        return error

# Alias for compatibility with your Flask app
get_intelligence_data = generate_and_save_intelligence

# Optional: Run as script to generate intelligence manually
if __name__ == "__main__":
    print(generate_and_save_intelligence("/data/temperature_agent_data_log.json", "temperature_agent", "°C"))
