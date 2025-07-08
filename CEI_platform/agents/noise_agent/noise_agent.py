import os, sys, time, json, random
from datetime import datetime
from flask import Flask, jsonify, request, Response, send_file


from .noise_requirements import get_requirements_data
from .noise_registration import load_metadata, register_with_controller, register_with_consul, metadata
from .noise_intelligence import generate_and_save_intelligence, get_intelligence_data
app = Flask(__name__)

PORT = 5002
DATA_LOG_PATH = "/data/noise_agent_data_log.json"

# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    data_point = {
        "timestamp": datetime.utcnow().isoformat(),
        "noise_level": round(random.uniform(40.0, 90.0), 2)
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

@app.route('/data/export/json')
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
            "measurement": "Noise",
            "value": entry["noise_level"]
        }
        for entry in raw_data
    ]

    return jsonify(formatted)

@app.route('/data/export/csv')
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
        csv_lines.append(f"{ts_epoch},Noise,{entry['noise_level']}")

    return Response(
        "\n".join(csv_lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=noiseagent_data.csv"}
    )

@app.route('/description')
def description():
    return jsonify(metadata)

@app.route('/intelligence')
def intelligence():
    # This will both compute and write the file
    result = generate_and_save_intelligence(DATA_LOG_PATH, metadata["agent_name"], metadata["unit"])
    return jsonify(result)
@app.route('/requirements')
def req():
    return jsonify(get_requirements_data(DATA_LOG_PATH, metadata["agent_name"], metadata["unit"]))

# -------- Main Flow -------- #
if __name__ == "__main__":
    time.sleep(5)
    if not load_metadata():
        register_with_controller()
    register_with_consul(port=5002)
    app.run(host="0.0.0.0", port=5002)
