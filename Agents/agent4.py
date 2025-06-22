from flask import Flask, jsonify, request, send_file
import uuid, json, http.client
import os, time
from datetime import datetime, timedelta
import random
import requests

app = Flask(__name__)

AGENT_NAME = "agent4"
PORT = 5003
UUID_PATH = "/data/agent4_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/agent4_data_log.json"

# -------- Metadata -------- #
metadata = {
    "uuid": "",
    "sensor_type": "Humidity Sensor",
    "frequency": "Every 10 seconds",
    "unit": "%",
    "location": "Zone D",
    "data_name": "humidity",
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
            print(f"[ERROR] Failed to register: {response.text}")
    except Exception as e:
        print(f"[ERROR] Registration exception: {e}")

def register_with_consul():
    try:
        service = {
            "ID": metadata["uuid"],
            "Name": AGENT_NAME,
            "Address": AGENT_NAME,
            "Port": PORT,
            "Check": {
                "HTTP": f"http://{AGENT_NAME}:{5003}/health",
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
    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "humidity": round(random.uniform(30.0, 90.0), 2)
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
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"agent": AGENT_NAME, "capabilities": "No data available"})

    try:
        with open(DATA_LOG_PATH, "r") as f:
            records = json.load(f)

        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent = [r["humidity"] for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return jsonify({"agent": AGENT_NAME, "capabilities": "No recent data in last 5 minutes"})

        return jsonify({
            "agent": AGENT_NAME,
            "average_humidity": sum(recent) / len(recent),
            "min_humidity": min(recent),
            "max_humidity": max(recent)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5003)
