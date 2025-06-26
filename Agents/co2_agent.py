
from flask import Flask, jsonify, request, send_file, Response
import uuid, json, http.client
import os, time
from datetime import datetime, timedelta
import random
import requests  
import sys

print("PYTHONPATH:", sys.path)

from data.co2_agent_capabilities import get_capabilities_data 

app = Flask(__name__)

AGENT_NAME = "co2_agent"
PORT = 5001
UUID_PATH = "/data/co2_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/co2_agent_data_log.json"

# ------- Metadata & UUID ------- #
metadata = {
    "uuid": "",
    "sensor_type": "CO2 Sensor",
    "frequency": "Every 10 seconds",
    "unit": "ppm",
    "location": "Zone B",
    "data_name": "co2_level",
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
        print(f"[ERROR] Controller registration failed: {e}")

def register_with_consul():
    try:
        service = {
            "ID": metadata["uuid"],
            "Name": AGENT_NAME,
            "Address": "co2_agent",
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://co2_agent:{5001}/health",
                "Interval": "10s"
            }
        }
        conn = http.client.HTTPConnection("consul", 8500)
        conn.request("PUT", "/v1/agent/service/register", body=json.dumps(service), headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        print(f"[INFO] Registered with Consul: {response.status} {response.reason}")
        conn.close()
    except Exception as e:
        print(f"[ERROR] Consul registration failed: {e}")

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    co2_level = random.randint(300, 600)

    if co2_level < 400:
        status = "Low"
    elif co2_level <= 500:
        status = "Moderate"
    else:
        status = "High"

    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "co2_level": co2_level,
        "co2_status": status
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

@app.route('/data/export/json', methods=['GET', 'POST'])
def export_json():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH, "r") as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 500

    formatted = [
        {
            "timestamp": int(datetime.fromisoformat(entry["timestamp"]).timestamp()),
            "measurement": "CO2",
            "value": entry["co2_level"]
        }
        for entry in raw_data
    ]

    return jsonify(formatted), 200

@app.route('/data/export/csv', methods=['GET', 'POST'])
def export_csv():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH, "r") as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 500

    csv_lines = ["Timestamp,Measurement,Value"]
    for entry in raw_data:
        ts_epoch = int(datetime.fromisoformat(entry["timestamp"]).timestamp())
        csv_lines.append(f"{ts_epoch},CO2,{entry['co2_level']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=co2_agent_data.csv"}
    )

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

        if request.method == 'GET':
            requirement = "average_co2"
            duration = 5
        else:
            req_data = request.get_json()
            requirement = req_data.get("requirement")
            duration = int(req_data.get("duration_minutes", 5))
            if not requirement:
                return jsonify({"error": "Missing 'requirement' field"}), 400

        cutoff = datetime.utcnow() - timedelta(minutes=duration)
        recent_records = [r for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent_records:
            return jsonify({"response": f"No recent data in last {duration} minutes"}), 200

        co2_values = [r["co2_level"] for r in recent_records]

        if requirement == "average_co2":
            value = round(sum(co2_values) / len(co2_values), 2)
        elif requirement == "min_co2":
            value = min(co2_values)
        elif requirement == "max_co2":
            value = max(co2_values)
        elif requirement == "co2_status":
            from collections import Counter
            statuses = [r.get("co2_status", "Unknown") for r in recent_records]
            value = Counter(statuses).most_common(1)[0][0]
        else:
            return jsonify({"error": f"Unknown requirement: {requirement}"}), 400

        return jsonify({
            "agent": AGENT_NAME,
            "requirement": requirement,
            "value": value,
            "unit": metadata["unit"] if "co2" in requirement else "status",
            "data_points_considered": len(recent_records)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------- Main Entry -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5001)
