import os
import json
import random
from datetime import datetime, timedelta
from . import temperature_statistics as stats  # Assumes functions for avg/max/min exist

DATA_LOG_PATH = "/app/agents/temperature_agent/temperature_agent_data_log.json"

def append_synthetic_data(data_log_path):
    os.makedirs(os.path.dirname(data_log_path), exist_ok=True)

    new_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": round(random.uniform(10.0, 40.0), 2),
        "status": random.choice(["Normal", "Elevated", "Critical"])
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

def generate_and_save_intelligence(data_log_path, agent_name, unit, port, url=None, status="Healthy"):
    def blank_result(agent_id, now):
        return {
            "agent_id": agent_id,
            "name": agent_name,
            "value": "NA",
            "unit": unit,
            "average_temperature": "NA",
            "max_temperature": "NA",
            "min_temperature": "NA",
            "last_updated": now,
            "url": url,
            "status": "NA"
        }

    try:
        now = datetime.utcnow().isoformat()

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

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return blank_result(agent_id, now)

        latest = recent[-1]
        temps = [r["temperature"] for r in recent if "temperature" in r and isinstance(r["temperature"], (int, float))]

        return {
            "agent_id": agent_id,
            "name": agent_name,
            "value": latest.get("temperature", "NA"),
            "unit": unit,
            "average_temperature": stats.calculate_average_temperature(temps) if temps else "NA",
            "max_temperature": stats.calculate_max_temperature(temps) if temps else "NA",
            "min_temperature": stats.calculate_min_temperature(temps) if temps else "NA",
            "last_updated": now,
            "url": url,
            "status": status
        }

    except Exception as e:
        fallback = blank_result(agent_name, datetime.utcnow().isoformat())
        fallback["error"] = str(e)
        return fallback

# Alias for compatibility
get_intelligence_data = generate_and_save_intelligence

# Optional test
if __name__ == "__main__":
    path = DATA_LOG_PATH
    append_synthetic_data(path)
    print(json.dumps(generate_and_save_intelligence(
        data_log_path=path,
        agent_name="temperature_agent",
        unit="°C",
        port=5004,
        url="http://localhost:5004",
        status="Healthy"
    ), indent=2))

