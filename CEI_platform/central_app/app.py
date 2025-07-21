from flask import Flask, render_template, request, jsonify
from consul_utils import get_registered_agents
from agent_utils import fetch_health, fetch_requirements , fetch_intelligence 
from datetime import datetime
import os, json, requests
from datetime import datetime

def blank_intelligence(agent_id, agent_name, url, reason=None):
    result = {
        "agent_id": agent_id,
        "name": agent_name,
        "value": "NA",
        "unit": "%",
        "average_humidity": "NA",
        "max_humidity": "NA",
        "min_humidity": "NA",
        "last_updated": datetime.utcnow().isoformat(),
        "url": url,
        "status": "Error",
    }
    if reason is not None:
        result["error"] = str(reason)
    return result

app = Flask(__name__)

# -------- Dashboard -------- #
@app.route('/')
def index():
    agents = get_registered_agents()
    health_data = fetch_health()
    requirements_data = fetch_requirements()

    for agent in agents:
        agent_id = agent['ID']
        agent["Health"] = health_data.get(agent_id, {}).get("status", "unknown")
        agent["Requirements"] = json.dumps(requirements_data.get(agent_id, {}), indent=2)

    return render_template("dashboard.html", agents=agents)

# -------- Get All Intelligence (Live from agents) -------- #
@app.route('/intelligence')


def intelligence():
    services = get_registered_agents()
    agent_info_by_name = {}

    for service in services:
        agent_id = service['ID']
        # Always prefer the registered ServiceName/Service (should be set)
        agent_name = service.get('ServiceName') or service.get('Service') or f"agent_{agent_id[:6]}"
        address = service.get('Address')  # now this should not be 127.0.0.1 in Docker!

        try:
            url = f"http://{address}:{service['Port']}/intelligence"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                name_key = data.get("name", agent_name)

                if name_key in agent_info_by_name:
                    name_key = f"{name_key}_{agent_id[:6]}"

                agent_info_by_name[name_key] = {
                    "agent_id": data.get("agent_id", agent_id),
                    "last_updated": data.get("last_updated", "NA"),
                    "name": data.get("name", agent_name),
                    "status": data.get("status", "NA"),
                    "unit": data.get("unit", "NA"),
                    "url": data.get("url", url),
                    "value": data.get("value", "NA")
                }
            else:
                print(f"[WARN] Non-200 from {agent_name} at {url}: {response.status_code} -- fallback to NA")
                raise Exception("Bad response code")
        except Exception as e:
            print(f"[ERROR] Failed to fetch from {agent_name} at {address}:{service['Port']} → {e} (Check network, port, and Consul Address field!)")
            fallback_name_key = agent_name
            if fallback_name_key in agent_info_by_name:
                fallback_name_key = f"{fallback_name_key}_{agent_id[:6]}"
            agent_info_by_name[fallback_name_key] = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "name": agent_name,
                "status": "NA",
                "value": "NA",
                "unit": "NA",
                "last_updated": datetime.utcnow().isoformat(),
                "url": f"http://{address}:{service['Port']}/intelligence"
            }

    return jsonify(fetch_intelligence())


# -------- Get Agent by ID -------- #
@app.route('/central/intelligence/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    all_agents = get_registered_agents()
    agent = next((a for a in all_agents if a['ID'] == agent_id), None)

    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    try:
        ip = agent['Address']
        port = agent['Port']
        url = f"http://{ip}:{port}/intelligence"
        resp = requests.get(url, timeout=2)
        intel = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"Error fetching /intelligence for {agent_id}: {e}")
        intel = {}

    return jsonify({
        "agent_id": agent_id,
        "agent_name": intel.get("name", agent.get("Service", "unknown")),
        "agent_description": intel.get("description", "No description available"),
        "intelligence": intel
    })

# -------- Export Requirements -------- #
@app.route('/requirements')
def requirements():
    return jsonify(fetch_requirements())

# -------- Start App -------- #
if __name__ == '__main__':
    os.environ['FLASK_ENV'] = 'development'
    app.run(debug=True, host="0.0.0.0", port=8000)
