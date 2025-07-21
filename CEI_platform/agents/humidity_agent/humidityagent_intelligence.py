import os
import json
from datetime import datetime, timedelta
from . import humidity_statistics as stats  # Contains avg/min/max functions

def generate_and_save_intelligence(data_log_path, agent_name, port, url=None, status="Healthy"):
    # Always accept agent_id, not just agent_name, for consistent ID handling
    def blank_result(agent_id, error=None):
        result = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": "NA",
            "unit": "%",
            "average_humidity": "NA",
            "max_humidity": "NA",
            "min_humidity": "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url or f"http://localhost:{port}" if port else "unknown",
            "status": "NA"  # Default to "NA"; set to "Error" if error supplied
        }
        if error:
            result["error"] = str(error)
            result["status"] = "Error"  # Mark status as error when appropriate
        return result

    agent_id = agent_name  # Default, updated from metadata if found
    try:
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)

        # Propagate error for all blank conditions
        if not os.path.exists(data_log_path):
            return blank_result(agent_id, error="Data log file missing.")

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return blank_result(agent_id, error="No records in data log.")

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return blank_result(agent_id, error="No recent data found (within 5 minutes).")

        latest = recent[-1]
        humidity_values = [r["humidity"] for r in recent if "humidity" in r]

        result_entry = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": latest.get("humidity_status", "NA"),
            "unit": "%",
            "average_humidity": stats.calculate_average_humidity(humidity_values) if humidity_values else "NA",
            "max_humidity": stats.calculate_max_humidity(humidity_values) if humidity_values else "NA",
            "min_humidity": stats.calculate_min_humidity(humidity_values) if humidity_values else "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url or f"http://localhost:{port}" if port else "unknown",
            "status": status
        }
        return result_entry

    except Exception as e:
        # Always use agent_id; add error string and Error status
        return blank_result(agent_id, error=f"Exception: {e}")

# Alias for external use
get_intelligence_data = generate_and_save_intelligence

# Optional direct test
if __name__ == "__main__":
    print(generate_and_save_intelligence(
        "/agents/humidity_agent/humidity_agent_data_log.json",
        "humidity_agent",
        port=5003,
        url="http://localhost:5003",
        status="Healthy"
    ))
