import os
import json
from datetime import datetime, timedelta
from . import temperature_statistics as stats  # Assumes functions for avg/max/min exist

def generate_and_save_intelligence(data_log_path, agent_name, unit, port, url=None, status="Healthy"):
    try:
        # Load UUID from metadata if available
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)
        else:
            agent_id = agent_name

        # Return fallback result
        def blank_result():
            return {
                "name": agent_name,
                "agent_id": agent_id,
                "value": "NA",
                "unit": unit,
                "average_temperature": "NA",
                "max_temperature": "NA",
                "min_temperature": "NA",
                "last_updated": datetime.utcnow().isoformat(),
                "url": url,
                "status": "NA"
            }

        # Load records
        if not os.path.exists(data_log_path):
            return blank_result()

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return blank_result()

        # Filter last 5 minutes of records
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return blank_result()

        latest = recent[-1]
        temps = [r["temperature"] for r in recent if "temperature" in r]

        result_entry = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": latest.get("temperature", "NA"),
            "unit": unit,
            "average_temperature": stats.calculate_average_temperature(temps) if temps else "NA",
            "max_temperature": stats.calculate_max_temperature(temps) if temps else "NA",
            "min_temperature": stats.calculate_min_temperature(temps) if temps else "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url,
            "status": status
        }

        return result_entry

    except Exception as e:
        return {
            "name": agent_name,
             "name": agent_name,
            "value": "NA",
            "unit": unit,
            "average_temperature": "NA",
            "max_temperature": "NA",
            "min_temperature": "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url,
            "status": "NA",
            "error": str(e)
        }

# Alias for compatibility
get_intelligence_data = generate_and_save_intelligence

# Optional test
if __name__ == "__main__":
    print(generate_and_save_intelligence(
        "/agents/temperature_agent/temperature_agent_data_log.json",
        "temperature_agent",
        unit="°C",
        port="5004",
        url="http://localhost:5004",
        status="Healthy"
    ))
