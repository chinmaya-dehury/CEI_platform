from flask import Flask, jsonify, request, send_file, Response
import os, json, time, random
from datetime import datetime
from .temperature_intelligence import get_intelligence_data  
from .temperature_requirements import get_requirements_data
from .temperature_registration import metadata, load_metadata, register_with_controller, register_with_consul
from .temperature_intelligence import generate_and_save_intelligence

app = Flask(__name__)
AGENT_NAME = "temperature_agent"

PORT = 5004
DATA_LOG_PATH = "/data/temperature_agent_data_log.json"

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    temp_value = round(random.uniform(20.0, 35.0), 2)

    if temp_value < 24.0:
        status = "Cold"
    elif temp_value <= 30.0:
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
            "measurement": "Temperature",
            "value": entry["temperature"]
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
        csv_lines.append(f"{ts_epoch},Temperature,{entry['temperature']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=temperatureagent_data.csv"}
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
    register_with_consul()
    app.run(host="0.0.0.0", port=5004)
