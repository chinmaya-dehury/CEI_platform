import os, sys, time, json, random
from datetime import datetime
from flask import Flask, jsonify, request, Response, send_file

from .temperature_requirements import get_requirements_data
from .temperature_registration import metadata, register_with_controller, register_with_consul
from .temperature_intelligence import generate_and_save_intelligence
from agents.temperature_agent.temperature_intelligence import append_synthetic_data



print("PYTHONPATH:", sys.path)

app = Flask(__name__)

AGENT_NAME = "temperature_agent"
PORT = 5004
DATA_LOG_PATH = "/app/agents/temperature_agent/temperature_agent_data_log.json"
METADATA_PATH = "/app/agents/temperature_agent/temperature_agent_metadata.json"
INTELLIGENCE_PATH = "/app/agents/temperature_agent/temperature_agent_intelligence.json"

# -------- Utility -------- #
def save_metadata_to_json(metadata, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(metadata, f, indent=4)

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    temp_value = round(random.uniform(20.0, 35.0), 2)
    status = "Cold" if temp_value < 24.0 else "Moderate" if temp_value <= 30.0 else "Hot"

    data_point = {
        "uuid": metadata.get("uuid", "NA"),
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": temp_value,
        "temperature_status": status,
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

    try:
        with open(DATA_LOG_PATH, "r") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 500

    return Response(
        json.dumps(raw_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=temperature_agent_data.json"}
    )

@app.route("/data/export/csv", methods=["GET"])
def export_csv():
    if not os.path.exists(DATA_LOG_PATH):
        return jsonify({"error": "No data available"}), 404

    try:
        with open(DATA_LOG_PATH, "r") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 500

    csv_lines = ["Timestamp,Measurement,Value"]
    for entry in raw_data:
        ts_epoch = int(datetime.fromisoformat(entry["timestamp"]).timestamp())
        csv_lines.append(f"{ts_epoch},Temperature,{entry['temperature']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=temperature_agent_data.csv"}
    )

@app.route("/intelligence")
def intelligence():
    result = generate_and_save_intelligence(
        DATA_LOG_PATH,
        metadata["agent_name"],
        metadata["unit"],
        PORT
    )

    os.makedirs(os.path.dirname(INTELLIGENCE_PATH), exist_ok=True)
    with open(INTELLIGENCE_PATH, "w") as f:
        json.dump(result, f, indent=2)

    return jsonify(result)

@app.route("/intelligence/export/json", methods=["GET"])
def export_intelligence_json():
    if not os.path.exists(INTELLIGENCE_PATH):
        return jsonify({"error": "No intelligence available"}), 404

    with open(INTELLIGENCE_PATH, "r") as f:
        raw_data = json.load(f)

    return Response(
        json.dumps(raw_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=temperature_agent_intelligence.json"}
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
    try:
        return send_file(METADATA_PATH, as_attachment=True, download_name="temperature_agent_metadata.json")
    except FileNotFoundError:
        return jsonify({"error": "UUID file not found"}), 404

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)

    register_with_controller()
    register_with_consul()

    save_metadata_to_json(metadata, METADATA_PATH)
    os.makedirs(os.path.dirname(DATA_LOG_PATH), exist_ok=True)
    append_synthetic_data(DATA_LOG_PATH)

    app.run(host="0.0.0.0", port=5004)
