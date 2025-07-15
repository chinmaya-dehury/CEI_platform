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
        print(f"Timestamp parse error: {e}")
        return False

def get_services_from_consul():
    try:
        res = requests.get(CONSUL_AGENT_SERVICES_URL)
        services = res.json()
        print("\n Discovered services from Consul:", list(services.keys()))
        return services
    except Exception as e:
        print(f"[Consul Error] Cannot get services: {e}")
        return {}

def fetch_intelligence(address, port):
    try:
        url = f"http://{address}:{port}/intelligence"
        res = requests.get(url, timeout=3)
        return res.json(), url
    except:
        return None, f"http://{address}:{port}"

def is_agent_online(address, port):
    try:
        res = requests.get(f"http://{address}:{port}/health", timeout=2)
        return res.status_code == 200
    except:
        return False

def search_intelligence(requirement_key):
    services = get_services_from_consul()
    exact_matches = []
    capable_but_stale = []
    incapable_agents = 0

    for service_id, meta in services.items():
        agent_name = meta.get("Service")
        address = meta.get("Address", "localhost")
        port = meta.get("Port")

        print(f"\n[Checking] {agent_name} at {address}:{port}")

        intelligence, url = fetch_intelligence(address, port)
        status = "online" if is_agent_online(address, port) else "offline"

        print(f"[Fetched Intelligence from {url}]: {json.dumps(intelligence, indent=2) if intelligence else 'None'}")
        print(f"[Status] {agent_name} is {status}")

        if not intelligence or "error" in intelligence:
            incapable_agents += 1
            print("[Skip] Invalid intelligence or contains error key")
            continue

        agent_id = intelligence.get("agent", agent_name)
        data = intelligence.get("data", {})
        capabilities = intelligence.get("capabilities", [])
        last_updated = intelligence.get("last_updated")

        normalized_data = {k.lower(): v for k, v in data.items()}
        normalized_caps = [{"parameter": cap.get("parameter", "").lower(), "unit": cap.get("unit")} for cap in capabilities]

        print(f"[Capabilities] {normalized_caps}")
        print(f"[Data Keys] {list(normalized_data.keys())}")
        print(f"[Last Updated] {last_updated}")

        if requirement_key in normalized_data and is_recent(last_updated):
            info = normalized_data[requirement_key]
            result_entry = {
                "agent_id": agent_id,
                "value": info.get("value"),
                "unit": info.get("unit"),
                "last_updated": last_updated,
                "url": url,
                "status": status
            }

            # Include optional stats if present
            for key in ["average_vehicle_count", "max_vehicle_count", "min_vehicle_count"]:
                if key in info:
                    result_entry[key] = info[key]

            exact_matches.append(result_entry)
            continue

        if any(cap["parameter"] == requirement_key for cap in normalized_caps):
            capable_but_stale.append({
                "agent_id": agent_id,
                "capability_status": "Capable but no recent data",
                "last_updated": last_updated or "unknown",
                "url": url,
                "status": status
            })
        else:
            incapable_agents += 1

    if exact_matches:
        return {
            "status": "Available",
            "message": f"Agents actively monitoring '{requirement_key}' were found.",
            "results": exact_matches
        }
    elif capable_but_stale:
        return {
            "status": "Partially Available",
            "message": f"Agents exist that can monitor '{requirement_key}', but no recent data is available.",
            "results": capable_but_stale
        }
    else:
        return {
            "status": "Unavailable",
            "message": f"No agents in the system are currently capable of monitoring '{requirement_key}'.",
            "agents_checked": len(services),
            "incapable_agents": incapable_agents
        }

@app.route("/search", methods=["GET"])
def search():
    requirement = request.args.get("requirement")
    if not requirement:
        return jsonify({"error": "Missing 'requirement' parameter"}), 400

    result = search_intelligence(requirement.lower())
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
