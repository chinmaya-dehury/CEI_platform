import json
import os
from datetime import datetime, timedelta
from . import noise_statistics as stats


INTELLIGENCE_PATH = "/data/noise_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit , port):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            result = {"error": "No data available"}
        else:
            # Filter last 5 minutes
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            recent = [
                r["noise_level"] for r in records
                if datetime.fromisoformat(r["timestamp"]) > cutoff
            ]
            if not recent:
                result = {"error": "No recent data in last 5 minutes"}
            else:
                result = {
     "average_noise": stats.calculate_average_noise(recent),
    "timestamp": stats.get_current_timestamp(),
    "min_noise": stats.calculate_min_noise(recent),
    "max_noise": stats.calculate_max_noise(recent),
    "data_points_analyzed": stats.get_data_point_count(recent),
    "unit": stats.get_unit(),
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
        # Attempt to save the error as well
        try:
            os.makedirs(os.path.dirname(INTELLIGENCE_PATH), exist_ok=True)
            with open(INTELLIGENCE_PATH, "w") as out:
                json.dump(error, out, indent=2)
        except Exception:
            pass
        return error

# Alias for compatibility with  Flask app
get_intelligence_data = generate_and_save_intelligence

# Optional: Run as script to generate intelligence manually
if __name__ == "__main__":
    print(generate_and_save_intelligence("/data/noise_agent_data_log.json", "noise_agent", "dB"))
