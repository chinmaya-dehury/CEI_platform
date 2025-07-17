import os
import json
from datetime import datetime, timedelta
from . import traffic_statistics as stats

def generate_and_save_intelligence(data_log_path, agent_name, port, url=None, status="Healthy"):
    try:
        # --- Try loading UUID from metadata file ---
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)  # fallback to name if uuid missing
        else:
            agent_id = agent_name

        # --- Handle if data log doesn't exist ---
        if not os.path.exists(data_log_path):
            return {
                "name": agent_name,  
                "agent_id": agent_id,
                "value": "NA",
                "unit": "NA",
                "average_vehicle_count": "NA",
                "max_vehicle_count": "NA",
                "min_vehicle_count": "NA",
                "last_updated": datetime.utcnow().isoformat(),
                "url": url,
                "status": "NA"
            }

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return {
                "name": agent_name,
                "agent_id": agent_id,
                "value": "NA",
                "unit": "NA",
                "average_vehicle_count": "NA",
                "max_vehicle_count": "NA",
                "min_vehicle_count": "NA",
                "last_updated": datetime.utcnow().isoformat(),
                "url": url,
                "status": "NA"
            }

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r for r in records if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return {
                "name": agent_name,
                "agent_id": agent_id,
                "value": "NA",
                "unit": "NA",
                "average_vehicle_count": "NA",
                "max_vehicle_count": "NA",
                "min_vehicle_count": "NA",
                "last_updated": datetime.utcnow().isoformat(),
                "url": url,
                "status": "NA"
            }

        latest = recent[-1]
        vehicle_counts = [r["vehicle_count"] for r in recent if "vehicle_count" in r]

        result_entry = {
             "name": agent_name,
            "agent_id": agent_id,
            "value": latest.get("congestion_status", "NA"),
            "unit": "%",
            "average_vehicle_count": stats.calculate_average_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "max_vehicle_count": stats.calculate_max_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "min_vehicle_count": stats.calculate_min_vehicle_count(vehicle_counts) if vehicle_counts else "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url,
            "status": status
        }

        return result_entry

    except Exception as e:
        return {
             "name": agent_name,
            "agent_id": agent_name,
            "value": "NA",
            "unit": "NA",
            "average_vehicle_count": "NA",
            "max_vehicle_count": "NA",
            "min_vehicle_count": "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url,
            "status": "NA",
            "error": str(e)
        }

# Alias for external use
get_intelligence_data = generate_and_save_intelligence

# Optional standalone test
if __name__ == "__main__":
    print(generate_and_save_intelligence(
        "/agents/traffic_agent/traffic_agent_data_log.json",
        "traffic_agent",
        port="5000",
        url="http://localhost:5000",
        status="Healthy"
    ))
