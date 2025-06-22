from flask import Flask, jsonify, request, send_file
import uuid, json, http.client
import os, csv, time, threading
from datetime import datetime
import random
import requests

app = Flask(__name__)

AGENT_NAME = "agent1"
PORT = 5000
UUID_PATH = "/data/agent1_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/agent1_data_log.json"

# ------- 1. Metadata & UUID Generation ------- #
metadata = {
    "uuid": "",
    "sensor_type": "Traffic Congestion Detector",
    "frequency": "Every 10 seconds",
    "unit": "vehicles/minute",
    "location": "Signal Point A",
    "data_name": "traffic_flow",
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
            "Address": "agent1",
            "Port": PORT,
            "Check": {
                "HTTP": f"http://agent1:{5000}/health",
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
        print(f"[ERROR] Failed to register with Consul using HTTPConnection: {e}")

# -------- Flask Endpoints -------- #

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "traffic_flow": random.randint(0, 100)
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
    now = datetime.utcnow()
    five_minutes_ago = now.timestamp() - 5 * 60

    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({
            "agent": AGENT_NAME,
            "capabilities": "No data available"
        })

    with open(DATA_LOG_PATH, "r") as f:
        try:
            history = json.load(f)
        except json.JSONDecodeError:
            return jsonify({
                "error": "Data history is corrupted"
            }), 500

    recent_values = []
    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
            if ts >= five_minutes_ago:
                recent_values.append(entry["traffic_flow"])
        except Exception:
            continue

    if not recent_values:
        return jsonify({
            "agent": AGENT_NAME,
            "capabilities": "No data from the last 5 minutes"
        })

    avg_val = sum(recent_values) / len(recent_values)
    min_val = min(recent_values)
    max_val = max(recent_values)

    return jsonify({
        "agent": AGENT_NAME,
        "capabilities": {
            "average_traffic_flow_last_5_minutes": round(avg_val, 2),
            "min_traffic_flow_last_5_minutes": min_val,
            "max_traffic_flow_last_5_minutes": max_val,
            "unit": "vehicles/minute",
            "data_points_considered": len(recent_values)
        }
    })

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5000)
