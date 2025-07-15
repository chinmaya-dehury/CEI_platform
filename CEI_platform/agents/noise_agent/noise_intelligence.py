import json
import os
from datetime import datetime, timedelta
from . import noise_statistics as stats

def generate_and_save_intelligence(data_log_path, agent_name, unit, port):
    try:
        if not os.path.exists(data_log_path):
            return {"error": "Data log not found"}

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {"error": "No data available"}

        # Filter last 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [
            r["noise_level"] for r in records
            if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return {"Nil"}

        result = {
            "agent": agent_name,
            "capabilities": [{"parameter": "noise", "unit": unit}],
            "data": {
                "noise": {
                    "average": stats.calculate_average_noise(recent),
                    "min": stats.calculate_min_noise(recent),
                    "max": stats.calculate_max_noise(recent),
                    "count": stats.get_data_point_count(recent)
                }
            },
            "unit": unit,
            "agent_url": f"http://localhost:{port}" if port else "unknown",
            "last_updated": datetime.utcnow().isoformat()
        }

        return result

    except Exception as e:
        return {"error": str(e)}

# Alias for Flask integration
get_intelligence_data = generate_and_save_intelligence

# Optional direct run
if __name__ == "__main__":
    print(generate_and_save_intelligence("/data/noise_agent_data_log.json", "noise_agent", "dB", 5002))
