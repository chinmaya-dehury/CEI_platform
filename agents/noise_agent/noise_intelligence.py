import os
import json
from datetime import datetime, timedelta
from . import noise_statistics as stats  # Ensure this has avg/min/max/count functions

def generate_and_save_intelligence(data_log_path, agent_name, port, url=None, status="Healthy"):
    def blank_result(agent_id, error=None):
        result = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": "NA",
            "unit": "dB",
            "average_noise": "NA",
            "max_noise": "NA",
            "min_noise": "NA",
            "data_point_count": "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url or f"http://localhost:{port}" if port else "unknown",
            "status": "NA"
        }
        if error:
            result["error"] = str(error)
        return result

    try:
        # Load agent UUID from metadata if available
        agent_dir = os.path.dirname(data_log_path)
        metadata_path = os.path.join(agent_dir, f"{agent_name}_metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                agent_id = metadata.get("uuid", agent_name)
        else:
            agent_id = agent_name

        if not os.path.exists(data_log_path):
            return blank_result(agent_id)

        with open(data_log_path, "r") as f:
            records = json.load(f)

        if not records:
            return blank_result(agent_id)

        # Filter for data within last 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [
            r for r in records
            if "timestamp" in r and datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return blank_result(agent_id)

        noise_values = [r["noise_level"] for r in recent if "noise_level" in r]

        result_entry = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": noise_values[-1] if noise_values else "NA",
            "unit": "dB",
            "average_noise": stats.calculate_average_noise(noise_values) if noise_values else "NA",
            "max_noise": stats.calculate_max_noise(noise_values) if noise_values else "NA",
            "min_noise": stats.calculate_min_noise(noise_values) if noise_values else "NA",
            "data_point_count": stats.get_data_point_count(noise_values) if noise_values else "NA",
            "last_updated": datetime.utcnow().isoformat(),
            "url": url or f"http://localhost:{port}" if port else "unknown",
            "status": status
        }

        return result_entry

    except Exception as e:
        return blank_result(agent_name, error=str(e))


# Alias for controller/dashboard
get_intelligence_data = generate_and_save_intelligence

# Optional standalone test
if __name__ == "__main__":
    print(generate_and_save_intelligence(
        "/agents/noise_agent/noise_agent_data_log.json",
        "noise_agent",
        port=5002,
        url="http://localhost:5002",
        status="Healthy"
    ))
