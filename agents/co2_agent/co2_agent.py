
from flask import Flask, jsonify, request, send_file, Response
import os, json, random, sys
from datetime import datetime
import uuid
from .registration import metadata, register_with_controller, register_with_consul
from .co2requirements import get_requirements_data
from .co2_agent_intelligence import generate_and_save_intelligence
import os
from agents.co2_agent.co2_agent_intelligence import append_synthetic_data
print("PYTHONPATH:", sys.path)

def save_metadata_to_json(metadata, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(metadata, f, indent=4)


app = Flask(__name__)

AGENT_NAME = "co2_agent"
PORT = 5001
DATA_LOG_PATH = "/app/agents/co2_agent/co2_agent_data_log.json"
intelligence_path = "/app/agents/co2_agent/co2_agent_intelligence.json"
metadata_path = "/app/agents/co2_agent/co2_agent_metadata.json"



# -------- Flask Endpoints -------- #
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/data')
def data():
    co2_level = random.randint(300, 600)
    status = "Low" if co2_level < 400 else "Moderate" if co2_level <= 500 else "High"

    data_point = {
        "uuid": metadata.get("uuid", "NA"),
        "timestamp": datetime.utcnow().isoformat(),
        "co2_level": co2_level,
        "co2_status": status,
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

    response = Response(
        json.dumps(raw_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=co2_agent_data.json"}
    )
    return response

@app.route('/data/export/csv', methods=['GET'])
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
def intelligence():
    result = generate_and_save_intelligence(
        DATA_LOG_PATH,
        metadata["agent_name"],
        metadata["unit"],
        PORT
    )

    # Define path to save the latest intelligence result
    intelligence_path = "/app/agents/co2_agent/co2_agent_intelligence.json"
    
    # Make sure the directory exists and save (overwrite)
    os.makedirs(os.path.dirname(intelligence_path), exist_ok=True)
    with open(intelligence_path, "w") as f:
        json.dump(result, f, indent=2)

    return jsonify(result)

@app.route("/intelligence/export/json", methods=["GET"])
def export_intelligence_json():
    result = generate_and_save_intelligence(
        DATA_LOG_PATH,
        metadata["agent_name"],
        metadata["unit"],
        PORT
    )

    if "error" in result:
        return jsonify(result), 400

    return Response(
        json.dumps(result, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=co2_agent_intelligence.json"}
    )

@app.route('/requirements', methods=["GET", "POST"])
def requirements_endpoint():
    return jsonify(
        get_requirements_data(DATA_LOG_PATH, AGENT_NAME, metadata["unit"])[0]
    )

@app.route("/download-uuid", methods=["GET"])
def download_uuid():
    uuid_file_path = "/agents/co2_agent/co2_agent_metadata.json"
    try:
        return send_file(uuid_file_path, as_attachment=True, download_name="co2_agent_metadata.json")
    except FileNotFoundError:
        return jsonify({"error": "UUID file not found"}), 404

if __name__ == "__main__":
    import time
    time.sleep(5)

    register_with_controller()
    register_with_consul()
    metadata_path = "/app/agents/co2_agent/co2_agent_metadata.json"
    save_metadata_to_json(metadata, metadata_path)

    #  Force synthetic data on startup
    from agents.co2_agent.co2_agent_intelligence import append_synthetic_data
    os.makedirs(os.path.dirname(DATA_LOG_PATH), exist_ok=True)
    append_synthetic_data(DATA_LOG_PATH)

    app.run(host="0.0.0.0", port=5001)