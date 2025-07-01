import uuid, json, http.client
import os, time
from datetime import datetime, timedelta
import random
import requests
import socket
import sys
from flask import Flask, jsonify, request, Response, send_file

print("PYTHONPATH:", sys.path)

from .humidityagent_requirements import get_requirements_data
from .humidityagent_intelligence import get_intelligence_data

app = Flask(__name__)

AGENT_NAME = "humidityagent"
PORT = 5003
UUID_PATH = "/data/humidityagent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/humidityagent_data_log.json"

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
            metadata.update(json.load(f))
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
        agent_ip = socket.gethostbyname(socket.gethostname())
        print(f"[INFO] Agent IP resolved as: {agent_ip}")

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_ip,
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{agent_ip}:{5003}/health",  # Dynamic port
                "Interval": "10s"
            }
        }

        conn = http.client.HTTPConnection("consul", 8500)
        conn.request(
            "PUT",
            "/v1/agent/service/register",
            body=json.dumps(service),
            headers={"Content-Type": "application/json"}
        )
        res = conn.getresponse()
        print(f"[INFO] Registered with Consul. Status: {res.status} {res.reason}")
        conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to register with Consul: {e}")
# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    humidity_value = round(random.uniform(30.0, 90.0), 2)

    if humidity_value < 40:
        status = "Low"
    elif humidity_value <= 60:
        status = "Moderate"
    else:
        status = "High"

    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "humidity": humidity_value,
        "humidity_status": status
    }

    os.makedirs(os.path.dirname(DATA_LOG_PATH), exist_ok=True)
    history = []
    if os.path.exists(DATA_LOG_PATH):
        with open(DATA_LOG_PATH) as f:
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
        with open(DATA_LOG_PATH) as f:
            try:
                return jsonify(json.load(f))
            except json.JSONDecodeError:
                return jsonify({"error": "History is corrupted"}), 500
    return jsonify([])

@app.route('/data/export/json', methods=['GET', 'POST'])
def export_json():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH) as f:
        try:
            records = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 500

    export = [
        {
            "timestamp": int(datetime.fromisoformat(entry["timestamp"]).timestamp()),
            "measurement": "Humidity",
            "value": entry["humidity"]
        } for entry in records
    ]

    return jsonify(export)

@app.route('/data/export/csv', methods=['GET', 'POST'])
def export_csv():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH) as f:
        try:
            records = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 500

    csv_lines = ["Timestamp,Measurement,Value"]
    for entry in records:
        ts_epoch = int(datetime.fromisoformat(entry["timestamp"]).timestamp())
        csv_lines.append(f"{ts_epoch},Humidity,{entry['humidity']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=humidityagent_data.csv"}
    )

@app.route('/description')
def description():
    return jsonify(metadata)

@app.route('/intelligence')
def intelligence():
    return jsonify(get_intelligence_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))

@app.route('/requirements', methods=['GET', 'POST'])
def req():
    return jsonify(get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5003)
