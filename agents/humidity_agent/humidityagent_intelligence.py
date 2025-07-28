import os
import json
import random
from datetime import datetime, timedelta
from agents.humidity_agent import humidity_statistics as stats

DATA_LOG_PATH = "/app/agents/humidity_agent/humidity_agent_data_log.json"

def append_synthetic_data(data_log_path):
    os.makedirs(os.path.dirname(data_log_path), exist_ok=True)

    # Generate synthetic humidity data
    new_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "humidity": round(random.uniform(30, 90), 2),  # %
        "humidity_status": random.choice(["Low", "Normal", "High"])
    }

    # Load existing data
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

    # Append new entry and save back
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
            "average_humidity": "NA",
            "max_humidity": "NA",
            "min_humidity": "NA",
            "last_updated": now,
            "url": url or None,
            "status": "NA"
        }

    try:
        now = datetime.utcnow().isoformat()

        # Load UUID from metadata
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)
        else:
            agent_id = agent_name

        if not os.path.exists(data_log_path):
            return blank_result(agent_id, now)

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records or not isinstance(records, list):
            return blank_result(agent_id, now)

        # Filter last 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [
            r for r in records
            if isinstance(r, dict)
            and "timestamp" in r
            and datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return blank_result(agent_id, now)

        humidity_values = [r.get("humidity") for r in recent if isinstance(r.get("humidity"), (int, float))]
        latest = recent[-1]

        return {
            "agent_id": agent_id,
            "name": agent_name,
            "value": latest.get("humidity_status", "NA"),
            "unit": "%",
            "average_humidity": stats.calculate_average_humidity(humidity_values) if humidity_values else "NA",
            "max_humidity": stats.calculate_max_humidity(humidity_values) if humidity_values else "NA",
            "min_humidity": stats.calculate_min_humidity(humidity_values) if humidity_values else "NA",
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

# Optional Test
if __name__ == "__main__":
    path = "/app/agents/humidity_agent/humidity_agent_data_log.json"
    append_synthetic_data(path)

    print(json.dumps(generate_and_save_intelligence(
        data_log_path=path,
        agent_name="humidity_agent",
        port=5003,
        url="http://localhost:5003",
        status="Healthy"
    ), indent=2))
