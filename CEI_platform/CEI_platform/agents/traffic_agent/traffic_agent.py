from flask import Flask, jsonify, request, send_file, Response
import uuid, json, http.client
import os, time, json, random, requests, sys, http.client
from datetime import datetime
import socket
from flask import Flask, jsonify, request, Response, send_file

from .traffic_requirements import get_requirements_data
from .traffic_agentintelligence import get_intelligence_data




print("PYTHONPATH:", sys.path)



app = Flask(__name__)

AGENT_NAME = "traffic_agent"
PORT = 5000
UUID_PATH = "/data/traffic_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"
DATA_LOG_PATH = "/data/traffic_agent_data_log.json"

# ------- Metadata & UUID ------- #
metadata = {
    "uuid": "",
    "sensor_type": "Traffic Congestion Sensor",
    "frequency": "Every 10 seconds",
    "unit": "%",
    "location": "Junction A1",
    "data_name": "congestion_level",
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
        # Dynamically resolve container IP
        agent_ip = socket.gethostbyname(socket.gethostname())
        print(f"[INFO] Resolved agent IP: {agent_ip}")

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_ip,  # Replaces metadata["address"]
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{agent_ip}:{5000}/health",  # Dynamic health check
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
    vehicle_count = random.randint(0, 100)

    if vehicle_count > 70:
        congestion_status = "High Congestion"
    elif vehicle_count > 40:
        congestion_status = "Moderate Congestion"
    else:
        congestion_status = "Low Congestion"

    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "vehicle_count": vehicle_count,
        "congestion_status": congestion_status
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
            "measurement": "Congestion",
            "value": entry["vehicle_count"]
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
        csv_lines.append(f"{ts_epoch},Congestion,{entry['vehicle_count']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_agent_data.csv"}
    )

@app.route('/description')
def description():
    return jsonify(metadata)

@app.route('/intelligence')
def intelligence():
    return jsonify(get_intelligence_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))

@app.route('/requirements', methods=['GET', 'POST'])
def get_req():  
    try:
        if request.method == 'GET':
            requirement = "average_vehicle_count"
            duration = 5
        else:
            req_data = request.get_json()
            requirement = req_data.get("requirement")
            duration = int(req_data.get("duration_minutes", 5))
            if not requirement:
                return jsonify({"error": "Missing 'requirement' field"}), 400

        result = get_requirements_data(
            data_log_path=DATA_LOG_PATH,
            agent_name=AGENT_NAME,
            duration=duration,
            requirement=requirement
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5000)
