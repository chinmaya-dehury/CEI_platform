import os
import json
from datetime import datetime, timedelta
import random
from . import traffic_statistics as stats


def append_synthetic_data(data_log_path):
    os.makedirs(os.path.dirname(data_log_path), exist_ok=True)

    new_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "vehicle_count": random.randint(0, 200),
        "congestion_status": random.choice(["Free Flow", "Moderate", "Heavy"])
    }

    if os.path.exists(data_log_path):
        with open(data_log_path, "r") as f:
            try:
                records = json.load(f)
                if not isinstance(records, list):
                    records = []
            except json.JSONDecodeError:
                records = []
    else:
        records = []

    records.append(new_entry)
    with open(data_log_path, "w") as f:
        json.dump(records[-200:], f, indent=2)  # retain last 200 records

def generate_and_save_intelligence(data_log_path, agent_name, port, url=None, status="Healthy"):
    def blank_result(agent_id, now):
        return {
            "agent_id": agent_id,
            "name": agent_name,
            "value": "NA",
            "unit": "%",
            "average_vehicle_count": "NA",
            "max_vehicle_count": "NA",
            "min_vehicle_count": "NA",
            "last_updated": now,
            "url": url or None,
            "status": "NA"
        }

    try:
        now = datetime.utcnow().isoformat()

        # --- Load UUID from metadata file ---
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)
        else:
            agent_id = agent_name

        # --- Check if the data log exists ---
        if not os.path.exists(data_log_path):
            return blank_result(agent_id, now)

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records or not isinstance(records, list):
            return blank_result(agent_id, now)

        # --- Filter records from the last 5 minutes ---
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [
            r for r in records
            if isinstance(r, dict)
            and "timestamp" in r
            and datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return blank_result(agent_id, now)

        # --- Extract vehicle counts ---
        vehicle_counts = [r.get("vehicle_count") for r in recent if isinstance(r.get("vehicle_count"), (int, float))]
        latest = recent[-1]

        return {
            "agent_id": agent_id,
            "name": agent_name,
            "value": latest.get("congestion_status", "NA"),
            "unit": "%",
            "average_vehicle_count": stats.calculate_average_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "max_vehicle_count": stats.calculate_max_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "min_vehicle_count": stats.calculate_min_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "last_updated": now,
            "url": url or None,
            "status": status
        }

    except Exception as e:
        fallback = blank_result(agent_name, datetime.utcnow().isoformat())
        fallback["error"] = str(e)
        return fallback

# Alias
get_intelligence_data = generate_and_save_intelligence

# Optional standalone test


    
if __name__ == "__main__":
    path = "/app/agents/traffic_agent/traffic_agent_data_log.json"
    append_synthetic_data(path)

    print(json.dumps(generate_and_save_intelligence(
        data_log_path="agents/traffic_agent/traffic_agent_data_log.json",
        agent_name="traffic_agent",
        port=5000,
        url="http://localhost:5000",
        status="Healthy"
    ), indent=2))
