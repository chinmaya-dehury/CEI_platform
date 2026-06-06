from flask import Flask, jsonify, request, send_file, Response, render_template, url_for
import os, json, random, sys
from datetime import datetime
import uuid
try:
    from agents.co2_agent.registration import (
        metadata,
        register_with_controller,
        register_with_consul,
    )
    from agents.co2_agent.co2requirements import get_requirements_data
    from .co2_agent_intelligence import generate_and_save_intelligence
    from agents.shared.intelligence_upload_handler import IntelligenceUploadHandler
    from agents.co2_agent.co2_agent_intelligence import append_synthetic_data
except ImportError:
    from registration import metadata, register_with_controller, register_with_consul
    from co2requirements import get_requirements_data
    from co2_agent_intelligence import generate_and_save_intelligence
    from agents.shared.intelligence_upload_handler import IntelligenceUploadHandler
    from co2_agent_intelligence import append_synthetic_data
print("PYTHONPATH:", sys.path)

def save_metadata_to_json(metadata, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(metadata, f, indent=4)


from flask import Blueprint
from flask import Flask
from jinja2 import Environment, FileSystemLoader
import pathlib

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Load menu structure from JSON file
import json as _json
MENU_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'endpoints_menu.json')
with open(MENU_PATH, 'r') as f:
    ENDPOINTS_MENU = _json.load(f)

# Landing page with sidebar and main panel
@app.route('/')
def index():
    return render_template('co2_agent_index.html', endpoints_menu=ENDPOINTS_MENU)

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
    # Initialize OpenWeather API client
    # api_client = WeatherAPIClient()
    
    # Extract latitude and longitude from metadata or use defaults (NYC)
    latitude = metadata.get("latitude", 40.7128)
    longitude = metadata.get("longitude", -74.0060)
    
    # Get CO2 level from OpenWeather API
    # api_result = api_client.get_co2_level(latitude, longitude)
    
    # Extract CO2 level and determine status
    # if api_result.get('status') == 'success':
    #     co2_level = api_result.get('co2_level', 400)
    # else:
    #     # If API fails, use fallback value
    #     co2_level = api_result.get('co2_level', random.randint(300, 600))

    co2_level = round(random.uniform(300, 900), 2)
    
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
        "agent_name": metadata["agent_name"],
        # "api_source": api_result.get('source', 'unknown'),
        # "execution_status": api_result.get('status', 'unknown')
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
                data = json.load(f)
            except json.JSONDecodeError:
                return jsonify([])
        if not isinstance(data, list) or not data:
            return jsonify([])
        return jsonify(data)
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

    # Save to co2_agent_intelligence.json
    intelligence_path = "/app/agents/co2_agent/co2_agent_intelligence.json"
    os.makedirs(os.path.dirname(intelligence_path), exist_ok=True)
    with open(intelligence_path, "w") as f:
        json.dump(result, f, indent=2)
    
    # Also save to intel_results/co2.json for quick access
    intel_results_path = "/app/agents/co2_agent/intel_results/co2.json"
    os.makedirs(os.path.dirname(intel_results_path), exist_ok=True)
    with open(intel_results_path, "w") as f:
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

@app.route("/upload-intelligence", methods=["POST"])
def upload_intelligence():
    """
    Upload a custom intelligence module with automatic OpenWeather API integration
    
    Expected form data:
    - file: Python file (.py)
    - replace: Optional bool to replace existing file
    
    Returns: JSON with upload status
    """
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided", "code": "NO_FILE"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected", "code": "NO_FILENAME"}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > IntelligenceUploadHandler.MAX_FILE_SIZE:
        return jsonify({
            "error": f"File too large. Maximum size: {IntelligenceUploadHandler.MAX_FILE_SIZE} bytes",
            "code": "FILE_TOO_LARGE"
        }), 413
    
    # Check if file extension is allowed
    if not IntelligenceUploadHandler.allowed_file(file.filename):
        return jsonify({
            "error": "Only .py files are allowed",
            "code": "INVALID_EXTENSION"
        }), 400
    
    try:
        # Read file content
        code = file.read().decode('utf-8')

        intelligence_name = request.form.get("intelligence_name", "").strip()
        description = request.form.get("description", "").strip()
        engine = request.form.get("engine", "").strip()
        version = request.form.get("version", "").strip()

        # Save uploaded file with API integration and auto-generated metadata
        success, message, metadata, registry_entry, execution_data = (
            IntelligenceUploadHandler.save_uploaded_file(
                file.filename,
                code,
                AGENT_NAME,
                intelligence_name=intelligence_name or None,
                description=description or None,
                engine=engine or None,
                version=version or None,
            )
        )
        
        if success:
            status_code = 200 if "already exists" in message.lower() else 201
            return jsonify({
                "status": "success",
                "message": message,
                "metadata": metadata,
                "registry_entry": registry_entry,
                "execution_data": execution_data,
                "next_steps": [
                    f"Call GET /intelligence to see '{metadata['module_name']}' in the registry"
                ]
            }), status_code
        else:
            return jsonify({
                "status": "error",
                "message": message,
                "code": "VALIDATION_FAILED"
            }), 400
    
    except UnicodeDecodeError:
        return jsonify({
            "error": "File is not a valid UTF-8 text file",
            "code": "DECODE_ERROR"
        }), 400
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}",
            "code": "UNKNOWN_ERROR"
        }), 500

@app.route("/upload-instructions", methods=["GET"])
def upload_instructions():
    """Get instructions for uploading intelligence modules"""
    
    instructions = IntelligenceUploadHandler.get_upload_instructions()
    
    return jsonify({
        "status": "success",
        "upload_endpoint": "/upload-intelligence",
        "method": "POST",
        "content_type": "multipart/form-data",
        **instructions
    }), 200

@app.route("/uploaded-intelligences", methods=["GET"])
def list_uploaded_intelligences():
    """List all uploaded intelligence modules with auto-generated metadata"""
    
    intel_path = f"/app/agents/co2_agent/intel_definitions"
    uploaded = []
    
    try:
        for filename in os.listdir(intel_path):
            if filename.endswith("_metadata.json"):
                metadata_file = os.path.join(intel_path, filename)
                with open(metadata_file, 'r') as f:
                    meta = json.load(f)
                    uploaded.append(meta)
        
        return jsonify({
            "status": "success",
            "count": len(uploaded),
            "uploaded_modules": uploaded
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/uploaded-intelligences/<filename>", methods=["DELETE"])
def delete_uploaded_intelligence(filename):
    """Delete an uploaded intelligence module"""
    
    # Secure filename
    from werkzeug.utils import secure_filename
    filename = secure_filename(filename)
    
    intel_path = f"/app/agents/co2_agent/intel_definitions"
    filepath = os.path.join(intel_path, filename)
    metadata_filepath = os.path.join(intel_path, f"{filename[:-3]}_metadata.json")
    data_filepath = os.path.join(intel_path, f"{filename[:-3]}.data")
    
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                "status": "error",
                "message": f"File '{filename}' not found"
            }), 404
        
        # Delete the module file
        os.remove(filepath)
        print(f"[INFO] Deleted intelligence module: {filename}")
        
        # Delete metadata file if it exists
        if os.path.exists(metadata_filepath):
            os.remove(metadata_filepath)
        
        # Delete data file if it exists
        if os.path.exists(data_filepath):
            os.remove(data_filepath)
        
        return jsonify({
            "status": "success",
            "message": f"Intelligence module '{filename}' deleted successfully",
            "deleted_file": filename,
            "next_steps": "Restart the co2_intelligence_service to apply changes"
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error deleting file: {str(e)}"
        }), 500

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

    app.run(host="0.0.0.0", port=5001, debug=True)
