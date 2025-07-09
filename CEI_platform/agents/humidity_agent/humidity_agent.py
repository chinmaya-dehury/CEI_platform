import os, sys, time, json, random
from datetime import datetime
from flask import Flask, jsonify, request, Response

from .humidityagent_requirements import get_requirements_data
from .humidityagent_intelligence import get_intelligence_data
from .humidity_registration import load_metadata, register_with_controller, register_with_consul, metadata
from .humidityagent_intelligence import generate_and_save_intelligence
AGENT_NAME = "humidity_agent"

app = Flask(__name__)

PORT = 5003
DATA_LOG_PATH = "/data/humidity_agent_data_log.json"
INTELLIGENCE_PATH = "/datahumidity_intelligence.json"

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

@app.route('/data/export/json')
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

@app.route('/data/export/csv')
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
    # This will both compute and write the file
    result = generate_and_save_intelligence(DATA_LOG_PATH, metadata["agent_name"], metadata["unit"], port=PORT)
    return jsonify(result)
@app.route('/requirements', methods=["GET", "POST"])
def requirements_endpoint():
    return jsonify(
        get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"])[0]
    )

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul(port=5003)
    app.run(host="0.0.0.0", port=5003)
