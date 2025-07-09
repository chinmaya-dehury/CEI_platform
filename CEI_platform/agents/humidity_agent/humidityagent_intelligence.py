# data/agent4_capabilities.py

# intelligence.py
import json
from datetime import datetime, timedelta
from . import humidity_statistics as stats

INTELLIGENCE_PATH = "/data/humidity_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit , port):
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
    "average_humidity": stats.calculate_average_humidity(recent),
    "timestamp": stats.get_current_timestamp(),
    "min_humidity": stats.calculate_min_humidity(recent),
    "max_humidity": stats.calculate_max_humidity(recent),
    "data_points_analyzed": stats.get_data_point_count(recent),
    "unit": stats.get_unit(),
    "agent": agent_name,
     "agent_url": f"http://localhost:{port}" if port else "unknown"
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
