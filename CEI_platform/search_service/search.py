from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import json

app = Flask(__name__)

CONSUL_HOST = "consul"
CONSUL_PORT = 8500
CONSUL_AGENT_SERVICES_URL = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/services"


def is_recent(timestamp_str, minutes=5):
    try:
        ts = isoparse(timestamp_str)
        return datetime.utcnow() - ts <= timedelta(minutes=minutes)
    except Exception as e:
        print(f"[Timestamp Parse Error] {e}")
        return False


def get_services_from_consul():
    try:
        res = requests.get(CONSUL_AGENT_SERVICES_URL)
        services = res.json()
        print("\n[Discovered Services]:", list(services.keys()))
        return services
    except Exception as e:
        print(f"[Consul Error] Could not fetch services: {e}")
        return {}


def fetch_intelligence(address, port):
    try:
        url = f"http://{address}:{port}/intelligence"
        res = requests.get(url, timeout=3)
        return res.json(), url
    except Exception as e:
        print(f"[Fetch Error] Could not reach {address}:{port} - {e}")
        return None, f"http://{address}:{port}"


def is_agent_online(address, port):
    try:
        res = requests.get(f"http://{address}:{port}/health", timeout=2)
        return res.status_code == 200
    except:
        return False


def search_intelligence(requirement_key):
    services = get_services_from_consul()
    results = {}
    total_checked = 0
    total_matched = 0

    requirement_key = requirement_key.lower()

    for service_id, meta in services.items():
        agent_service_name = meta.get("Service")
        address = meta.get("Address", "localhost")
        port = meta.get("Port")
        total_checked += 1

        print(f"\n[Checking] {agent_service_name} at {address}:{port}")

        intelligence, url = fetch_intelligence(address, port)
        status = "Healthy" if is_agent_online(address, port) else "Unhealthy"

        print(f"[Fetched Intelligence from {url}]: {json.dumps(intelligence, indent=2) if intelligence else 'None'}")
        print(f"[Status] {agent_service_name} is {status}")

        # Use agent_id and name from intelligence JSON if present, else fall back to Consul service name
        agent_id = intelligence.get("agent_id", agent_service_name) if intelligence else agent_service_name
        agent_name = intelligence.get("name", agent_service_name) if intelligence else agent_service_name

        # ---- FIX: match on both agent_id and agent_name ----
        if (requirement_key not in str(agent_id).lower()) and \
           (requirement_key not in str(agent_name).lower()):
            continue

        total_matched += 1
        last_updated = intelligence.get("last_updated") if (intelligence and isinstance(intelligence, dict)) else None
        recent = is_recent(last_updated) if last_updated else False
        info = intelligence if (intelligence and recent) else {}

        result_entry = {
            "name": agent_name,
            "agent_id": agent_id,
            "value": info.get("value", "NA"),
            "unit": info.get("unit", "NA"),
            "average_vehicle_count": info.get("average_vehicle_count", "NA"),
            "max_vehicle_count": info.get("max_vehicle_count", "NA"),
            "min_vehicle_count": info.get("min_vehicle_count", "NA"),
            "last_updated": last_updated if last_updated else datetime.utcnow().isoformat(),
            "url": url,
            "status": status
        }

        results[agent_id] = result_entry

    return total_checked, total_matched, results


@app.route("/search", methods=["GET"])
def search():
    requirement = request.args.get("requirement")
    if not requirement:
        return jsonify({"error": "Missing 'requirement' parameter"}), 400

    total_checked, total_matched, results = search_intelligence(requirement.lower())

    if total_matched == 0:
        return jsonify({
            "agents_checked": total_checked,
            "incapable_agents": total_checked,
            "message": f"No agents in the system are currently capable of monitoring '{requirement}'.",
            "status": "Unavailable"
        }), 200

    return jsonify({
        "results": results,
        "message": f"{total_checked} agents checked. {total_matched} matched.",
        "status": "Partial" if total_matched < total_checked else "Success"
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
