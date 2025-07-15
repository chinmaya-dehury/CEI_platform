from flask import Flask, jsonify, request, Response, send_file
import os, json, random, sys
from datetime import datetime
import uuid

from .humidity_registration import metadata, register_with_controller, register_with_consul
from .humidityagent_requirements import get_requirements_data
from .humidityagent_intelligence import generate_and_save_intelligence

print("PYTHONPATH:", sys.path)

app = Flask(__name__)

AGENT_NAME = "humidity_agent"
PORT = 5003
DATA_LOG_PATH = "/agents/humidity_agent/humidity_agent_data_log.json"

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
        "humidity_status": status,
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

@app.route("/data/export/json", methods=["GET"])
def export_json():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 500

    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=humidity_agent_data.json"}
    )

@app.route("/data/export/csv", methods=["GET"])
def export_csv():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    with open(DATA_LOG_PATH, "r") as f:
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
        headers={"Content-Disposition": "attachment; filename=humidity_agent_data.csv"}
    )

@app.route("/intelligence")
def intelligence():
    result = generate_and_save_intelligence(
        DATA_LOG_PATH,
        metadata["agent_name"],
        PORT
    )
    return jsonify(result)

@app.route("/intelligence/export/json", methods=["GET"])
def export_intelligence_json():
    result = generate_and_save_intelligence(
        DATA_LOG_PATH,
        metadata["agent_name"],
        PORT
    )

    if "error" in result:
        return jsonify(result), 400

    return Response(
        json.dumps(result, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=humidity_agent_intelligence.json"}
    )

@app.route('/description')
def description():
    return jsonify(metadata)

@app.route('/requirements', methods=["GET", "POST"])
def requirements_endpoint():
    return jsonify(
        get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"])[0]
    )

@app.route("/download-uuid", methods=["GET"])
def download_uuid():
    uuid_file_path = "/agents/humidity_agent/humidity_agent_metadata.json"
    try:
        return send_file(uuid_file_path, as_attachment=True, download_name="humidity_agent_metadata.json")
    except FileNotFoundError:
        return jsonify({"error": "UUID file not found"}), 404

# -------- Main Flow -------- #
if __name__ == "__main__":
    import time
    time.sleep(5)

    register_with_controller()
    register_with_consul()
    app.run(host="0.0.0.0", port=5003)
