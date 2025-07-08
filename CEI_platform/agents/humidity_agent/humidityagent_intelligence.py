# data/agent4_capabilities.py

# intelligence.py
import json
from datetime import datetime, timedelta

INTELLIGENCE_PATH = "/data/humidity_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            result = {"error": "No data available"}
        else:
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            recent = [
                r["humidity"] for r in records
                if datetime.fromisoformat(r["timestamp"]) > cutoff
            ]
            if not recent:
                result = {"error": "No recent data in last 5 minutes"}
            else:
                result = {
                    "average_humidity": round(sum(recent) / len(recent), 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "min_humidity": min(recent),
                    "max_humidity": max(recent),
                    "data_points_analyzed": len(recent),
                    "unit": unit
                }
        # Save to JSON file
        with open(INTELLIGENCE_PATH, "w") as out:
            json.dump(result, out, indent=2)
        return result

    except Exception as e:
        error = {"error": str(e)}
        with open(INTELLIGENCE_PATH, "w") as out:
            json.dump(error, out, indent=2)
        return error

# Alias for compatibility with your Flask app
get_intelligence_data = generate_and_save_intelligence

# Optional: Run as script to generate intelligence
if __name__ == "__main__":
    print(generate_and_save_intelligence("data/humidityagent_data_log.json", "humidity_agent", "%"))
