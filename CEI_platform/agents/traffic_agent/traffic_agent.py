from flask import Flask, jsonify, request, Response, send_file
import os, json, random, sys
from datetime import datetime
import uuid
from .traffic_registration import metadata, register_with_controller, register_with_consul
from .traffic_requirements import get_requirements_data
from .traffic_agentintelligence import generate_and_save_intelligence
import requests

CENTRAL_APP_URL = "http://dashboard:8000/receive_data"
INTELLIGENCE_FILE = "/agents/traffic_agent/traffic_agent_01_intelligence.json"
DATA_LOG_PATH = "/agents/traffic_agent/traffic_agent_data_log.json"
AGENT_NAME = "traffic_agent"
PORT = 5000

print("PYTHONPATH:", sys.path)

app = Flask(__name__)

# -------- Flask Endpoints -------- #

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


@app.route('/data')
def data():
    vehicle_count = random.randint(0, 100)
    congestion_status = (
        "High Congestion" if vehicle_count > 70 else
        "Moderate Congestion" if vehicle_count > 40 else
        "Low Congestion"
    )

    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "vehicle_count": int(uuid.uuid4().int % 100),
        "congestion_status": congestion_status,
        "sensor_type": metadata["sensor_type"],
        "frequency": metadata["frequency"],
        "unit": metadata["unit"],
        "location": metadata["location"],
        "data_name": metadata["data_name"],
        "agent_name": metadata["agent_name"]
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
    return jsonify({"error": "No data log found"}), 404


@app.route("/data/export/json", methods=["GET"])
def export_json():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    try:
        with open(DATA_LOG_PATH, "r") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 500

    return Response(
        json.dumps(raw_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=traffic_agent_data.json"}
    )


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
    result = generate_and_save_intelligence(DATA_LOG_PATH, metadata["agent_name"], PORT)

    wrapped_data = {
        "agent_name": metadata["agent_name"],
        "agent_id": "traffic_agent_01",
        "agent_description": "Monitors traffic at junction X",
        "intelligence": result
    }

    os.makedirs(os.path.dirname(INTELLIGENCE_FILE), exist_ok=True)
    with open(INTELLIGENCE_FILE, "w") as f:
        json.dump(wrapped_data, f, indent=2)

    try:
        response = requests.post(CENTRAL_APP_URL, json=wrapped_data)
        print(" POSTED to central app:", response.status_code)
        print(" Response:", response.text)
    except Exception as e:
        print(" Failed to post to central app:", e)

    # Return the entire wrapped_data, not just result!
    return jsonify(wrapped_data)


@app.route("/intelligence/export/json", methods=["GET"])
def export_intelligence_json():
    result = generate_and_save_intelligence(DATA_LOG_PATH, metadata["agent_name"], PORT)
    if "error" in result:
        return jsonify(result), 400

    return Response(
        json.dumps(result, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=traffic_agent_intelligence.json"}
    )


@app.route('/requirements', methods=["GET", "POST"])
def requirements_endpoint():
    return jsonify(
        get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"])[0]
    )


@app.route("/download-uuid", methods=["GET"])
def download_uuid():
    uuid_file_path = "/agents/traffic_agent/traffic_agent_metadata.json"
    try:
        return send_file(uuid_file_path, as_attachment=True, download_name="traffic_agent_metadata.json")
    except FileNotFoundError:
        return jsonify({"error": "UUID file not found"}), 404


@app.route('/central/intelligence', methods=['GET'])
def central_intelligence():
    try:
        response = requests.get('http://dashboard:8000/intelligence')
        return Response(
            json.dumps(response.json(), indent=2),
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def send_intelligence_to_central(agent_id, agent_name, agent_description, intelligence_dict):
    data = {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agent_description": agent_description,
        "intelligence": intelligence_dict
    }
    try:
        response = requests.post(CENTRAL_APP_URL, json=data)
        print("Posted to central app:", response.status_code, response.text)
    except Exception as e:
        print("Failed to post to central app:", e)


# -------- Main Flow -------- #
if __name__ == "__main__":
    import time
    time.sleep(5)
    register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5000)
