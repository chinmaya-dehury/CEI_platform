
from flask import Flask, jsonify, request, send_file, Response
import uuid, json, time, os, random, sys
from datetime import datetime
import requests  

from . import co2requirements as requirements
from . import co2_agent_intelligence as intelligence
from .co2_agent_intelligence import get_intelligence_data
from .co2requirements import get_requirements_data
from .registration import load_metadata, register_with_controller, register_with_consul  #  Use external registration

print("PYTHONPATH:", sys.path)

app = Flask(__name__)

AGENT_NAME = "co2_agent"
PORT = 5001
UUID_PATH = "/data/co2_agent_metadata.json"
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

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    co2_level = random.randint(300, 600)
    status = "Low" if co2_level < 400 else "Moderate" if co2_level <= 500 else "High"
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

@app.route('/intelligence')
def intelligence_endpoint():
    return jsonify(get_intelligence_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))

@app.route('/requirements')
def requirements_endpoint():
    return jsonify(get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"]))

# -------- Main Entry -------- #
if __name__ == "__main__":
    time.sleep(5)  # Give controller/consul time to start in Docker
    if not load_metadata(metadata):
        register_with_controller(metadata)
    register_with_consul(metadata, 5001)
    app.run(host="0.0.0.0", port=5001)
