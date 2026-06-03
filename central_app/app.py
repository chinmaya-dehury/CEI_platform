from flask import Flask, render_template, request, jsonify
from consul_utils import get_registered_agents
from agent_utils import fetch_health, fetch_requirements , fetch_intelligence 
from datetime import datetime
import os, json, requests
from datetime import datetime
from repository_service import collect_repository
from intelligence_creator import forward_intelligence_to_agent

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

# -------- Get Repository -------- #

@app.route("/repository")
def repository():

    data = collect_repository()

    return render_template(
        "repository.html",
        repository=data
    )


@app.route("/api/repository")
def api_repository():

    return jsonify(collect_repository())

# -------- Add Intelligence -------- #
@app.route('/add-intelligence', methods=['POST'])
def add_intelligence():

    try:

        file = request.files.get("file")

        agent_name = request.form.get("agent_name")

        intelligence_name = request.form.get("intelligence_name")

        description = request.form.get("description", "")

        engine = request.form.get("engine", "").strip()

        version = request.form.get("version", "").strip()

        if not file:
            return jsonify({
                "error": "No file uploaded"
            }), 400

        if not agent_name:
            return jsonify({
                "error": "Agent name missing"
            }), 400

        result = forward_intelligence_to_agent(
            agent_name=agent_name,
            intelligence_name=intelligence_name,
            description=description,
            file=file,
            engine=engine,
            version=version,
        )

        if result["status"] != "success":
            message = result.get("message", "Upload failed")
            http_status = result.get("http_status", 500)
            status_code = 500
            if http_status in (400, 409):
                status_code = http_status
            elif "already exists" in message.lower():
                status_code = 409

            return jsonify({
                "status": "error",
                "message": message,
                "error": message,
                "code": "VALIDATION_FAILED" if status_code == 409 else "UPLOAD_FAILED",
            }), status_code

        agent_response = result.get("response") or {}
        metadata = agent_response.get("metadata") or {}
        registry_entry = agent_response.get("registry_entry") or {}

        payload = {
            "status": "success",
            "agent_name": result.get("agent_name"),
            "intelligence_name": result.get("intelligence_name"),
            "uuid": registry_entry.get("uuid") or metadata.get("intelligence_id"),
            "intelligence_id": (
                registry_entry.get("intelligence_id")
                or registry_entry.get("uuid")
                or metadata.get("intelligence_id")
            ),
            "description": registry_entry.get("description") or description,
            "implementation_path": registry_entry.get("implementation_path") or metadata.get("implementation_path"),
            "result_path": registry_entry.get("result_path"),
            "data": agent_response.get("execution_data") or registry_entry.get("result_data"),
            "created_at": registry_entry.get("created_at") or metadata.get("created_at"),
            "extension": registry_entry.get("extension") or "py",
            "engine": registry_entry.get("engine") or engine,
            "version": registry_entry.get("version") or version,
            "engine_installation": registry_entry.get("engine_installation") or metadata.get("engine_installation"),
            "message": agent_response.get("message", "Upload successful"),
        }

        # #region agent log
        try:
            import json as _json
            _log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug-552a44.log")
            with open(_log_path, "a", encoding="utf-8") as _lf:
                _lf.write(_json.dumps({"sessionId": "552a44", "location": "app.py:add_intelligence", "message": "success payload", "data": {"keys": list(payload.keys()), "hasUuid": bool(payload.get("uuid")), "hasPath": bool(payload.get("implementation_path"))}, "timestamp": int(datetime.utcnow().timestamp() * 1000), "hypothesisId": "A"}) + "\n")
        except Exception:
            pass
        # #endregion

        return jsonify(payload), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# -------- Get Agents List -------- #
@app.route('/get-agents', methods=['GET'])
def get_agents():
    """Get list of available agents. Returns hardcoded list for fast response."""
    
    # Known agents in the system - FALLBACK LIST with correct ports
    DEFAULT_AGENTS = [
        {"name": "traffic_agent", "id": "traffic_agent", "port": 5000},
        {"name": "co2_agent", "id": "co2_agent", "port": 5001},
        {"name": "noise_agent", "id": "noise_agent", "port": 5002},
        {"name": "humidity_agent", "id": "humidity_agent", "port": 5003},
        {"name": "temperature_agent", "id": "temperature_agent", "port": 5004},
    ]
    
    return jsonify(DEFAULT_AGENTS), 200

# -------- Start App -------- #
if __name__ == '__main__':
    os.environ['FLASK_ENV'] = 'development'
    app.run(debug=True, host="0.0.0.0", port=8000)
