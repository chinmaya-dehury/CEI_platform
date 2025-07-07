import json
from datetime import datetime, timedelta
from collections import Counter

INTELLIGENCE_PATH = "/data/co2_agent_intelligence.json"

def generate_and_save_intelligence(data_log_path, agent_name, unit):
    try:
        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            result = {"error": "No data available"}
        else:
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            recent = [
                r for r in records
                if datetime.fromisoformat(r["timestamp"]) > cutoff
            ]
            if not recent:
                result = {"error": "No recent data in last 5 minutes"}
            else:
                co2_values = [r["co2_level"] for r in recent]
                statuses = [r.get("co2_status", "Unknown") for r in recent]
                result = {
                    "average_co2": round(sum(co2_values) / len(co2_values), 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "min_co2": min(co2_values),
                    "max_co2": max(co2_values),
                    "most_common_co2_status": Counter(statuses).most_common(1)[0][0],
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
    print(generate_and_save_intelligence("/data/co2_agent_data_log.json", "co2_agent", "ppm"))
