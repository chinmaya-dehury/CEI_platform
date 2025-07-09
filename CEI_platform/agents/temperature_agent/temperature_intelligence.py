import os
import json
from datetime import datetime, timedelta
from collections import Counter
from . import temperature_statistics as stats


INTELLIGENCE_PATH = "/data/temperature_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit , port):
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
                    "data_points_analyzed": stats.get_data_point_count(values),
                    "average_temperature": stats.calculate_average_temperature(values),
                    "timestamp": stats.get_current_timestamp(),
                    "min_temperature": stats.calculate_min_temperature(values),
                    "max_temperature": stats.calculate_max_temperature(values),
                    "unit": stats.get_unit(),
                    "status_distribution": stats.get_status_distribution(statuses),
                    "agent": agent_name,
                    "agent_url": f"http://localhost:{port}" if port else "unknown"
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
