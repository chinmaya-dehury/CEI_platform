from flask import Flask, jsonify, request, send_file
import uuid, json, http.client
import os, time
from datetime import datetime
import random
import requests
import sys
from datetime import timedelta 
print("PYTHONPATH:", sys.path)

from data.agent5_capabilities import get_capabilities_data  # ✅ imported

app = Flask(__name__)

AGENT_NAME = "agent5"
PORT = 5004
UUID_PATH = "/data/agent5_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/agent5_data_log.json"

# -------- Metadata -------- #
metadata = {
    "uuid": "",
    "sensor_type": "Temperature Sensor",
    "frequency": "Every 10 seconds",
    "unit": "°C",
    "location": "Zone E",
    "data_name": "temperature",
    "agent_name": AGENT_NAME
}

def save_metadata():
    os.makedirs(os.path.dirname(UUID_PATH), exist_ok=True)
    with open(UUID_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

def load_metadata():
    if os.path.exists(UUID_PATH):
        with open(UUID_PATH) as f:
            loaded = json.load(f)
            metadata.update(loaded)
        print(f"[INFO] Loaded metadata and UUID: {metadata['uuid']}")
        return True
    return False

def register_with_controller():
    try:
        response = requests.post(CONTROLLER_URL, json=metadata)
        if response.status_code == 200:
            metadata["uuid"] = response.json().get("uuid")
            print(f"[INFO] UUID received from controller: {metadata['uuid']}")
            save_metadata()
        else:
            print(f"[ERROR] Failed to register with controller: {response.text}")
    except Exception as e:
        print(f"[ERROR] Controller registration exception: {e}")

def register_with_consul():
    try:
        service = {
            "ID": metadata["uuid"],
            "Name": AGENT_NAME,
            "Address": AGENT_NAME,
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{AGENT_NAME}:{PORT}/health",
                "Interval": "10s"
            }
        }
        json_data = json.dumps(service)
        headers = {"Content-Type": "application/json"}

        conn = http.client.HTTPConnection("consul", 8500)
        conn.request("PUT", "/v1/agent/service/register", body=json_data, headers=headers)
        response = conn.getresponse()
        print(f"[INFO] Registered with Consul. Status: {response.status} {response.reason}")
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to register with Consul: {e}")

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    temp_value = round(random.uniform(20.0, 35.0), 2)

    # Temperature category logic
    if temp_value < 24.0:
        status = "Cold"
    elif 24.0 <= temp_value <= 30.0:
        status = "Moderate"
    else:
        status = "Hot"

    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": temp_value,
        "temperature_status": status
    }

    os.makedirs(os.path.dirname(DATA_LOG_PATH), exist_ok=True)
    history = []
    if os.path.exists(DATA_LOG_PATH):
        with open(DATA_LOG_PATH, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

    history.append(data_point)

    with open(DATA_LOG_PATH, "w") as f:
        json.dump(history, f, indent=2)

    return jsonify(data_point)

@app.route('/data/history')
def data_history():
    if os.path.exists(DATA_LOG_PATH):
        with open(DATA_LOG_PATH, "r") as f:
            try:
                return jsonify(json.load(f))
            except json.JSONDecodeError:
                return jsonify({"error": "History is corrupted"}), 500
    return jsonify([])

@app.route('/data/export')
def export_data():
    if os.path.exists(DATA_LOG_PATH):
        return send_file(DATA_LOG_PATH, as_attachment=True)
    else:
        return jsonify({"error": "No data log found"}), 404

@app.route('/description')
def description():
    return jsonify(metadata)

@app.route('/capabilities')
def capabilities():
    return jsonify(get_capabilities_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))
@app.route('/req', methods=['GET', 'POST'])
def handle_req():
    try:
        if not os.path.exists(DATA_LOG_PATH):
            return jsonify({"error": "No data log found"}), 404

        with open(DATA_LOG_PATH, "r") as f:
            records = json.load(f)

        # Handle GET (default view) or POST (custom query)
        if request.method == 'GET':
            requirement = "average_temperature"
            duration = 5
        else:
            req_data = request.get_json()
            requirement = req_data.get("requirement")
            duration = int(req_data.get("duration_minutes", 5))

            if not requirement:
                return jsonify({"error": "Missing 'requirement' field"}), 400

        # Filter records from the past 'duration' minutes
        cutoff = datetime.utcnow() - timedelta(minutes=duration)
        recent = [r["temperature"] for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return jsonify({"response": f"No recent data in last {duration} minutes"}), 200

        # Compute based on requirement
        if requirement == "average_temperature":
            value = round(sum(recent) / len(recent), 2)
        elif requirement == "min_temperature":
            value = min(recent)
        elif requirement == "max_temperature":
            value = max(recent)
        else:
            return jsonify({"error": f"Unknown requirement: {requirement}"}), 400

        return jsonify({
            "agent": AGENT_NAME,
            "requirement": requirement,
            "value": value,
            "unit": metadata["unit"],
            "data_points_considered": len(recent)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5004)
