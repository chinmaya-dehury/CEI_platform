import os
import json
from datetime import datetime, timedelta
from collections import Counter

INTELLIGENCE_PATH = "/data/traffic_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit=None):
    try:
        if not os.path.exists(data_log_path):
            result = {"error": "Data log not found"}
        else:
            with open(data_log_path, "r") as f:
                records = json.load(f)

            if not records:
                result = {"error": "No data available"}
            else:
                # Last 5 minutes only
                cutoff = datetime.utcnow() - timedelta(minutes=5)
                recent = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

                if not recent:
                    result = {"error": "No recent data in last 5 minutes"}
                else:
                    vehicle_counts = [r["vehicle_count"] for r in recent]
                    statuses = [r.get("congestion_status", "Unknown") for r in recent]

                    result = {
                        "agent": agent_name,
                        "average_vehicle_count": round(sum(vehicle_counts) / len(vehicle_counts), 2),
                        "timestamp": datetime.utcnow().isoformat(),
                        "min_vehicle_count": min(vehicle_counts),
                        "max_vehicle_count": max(vehicle_counts),
                        "most_common_congestion_status": Counter(statuses).most_common(1)[0][0],
                        "data_points_analyzed": len(recent)
                    }
                    if unit:
                        result["unit"] = unit

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
    print(generate_and_save_intelligence("/data/traffic_agent_data_log.json", "traffic_agent"))
