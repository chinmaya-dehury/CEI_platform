from flask import Flask, jsonify, request, Response, send_file, render_template
import os, json, random, sys
from datetime import datetime
import uuid

try:
    from agents.humidity_agent.humidity_registration import (
        metadata,
        register_with_controller,
        register_with_consul,
    )
    from agents.humidity_agent.humidityagent_requirements import get_requirements_data
    from agents.humidity_agent.humidityagent_intelligence import (
        generate_and_save_intelligence,
        append_synthetic_data,
    )
    from agents.shared.intelligence_upload_handler import IntelligenceUploadHandler

except ImportError:
    from .humidity_registration import (
        metadata,
        register_with_controller,
        register_with_consul,
    )
    from .humidityagent_requirements import get_requirements_data
    from .humidityagent_intelligence import (
        generate_and_save_intelligence,
        append_synthetic_data,
    )
    from agents.shared.intelligence_upload_handler import IntelligenceUploadHandler
metadata_path = "/app/agents/humidity_agent/humidity_agent_metadata.json"


def save_metadata_to_json(metadata, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(metadata, f, indent=4)

print("PYTHONPATH:", sys.path)

app = Flask(__name__, template_folder='templates')

# Load menu structure from JSON file for template
MENU_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'endpoints_menu.json')
try:
    with open(MENU_PATH, 'r') as _m:
        ENDPOINTS_MENU = json.load(_m)
except Exception:
    ENDPOINTS_MENU = []


@app.route('/')
def index():
    return render_template('humidity_agent_index.html', endpoints_menu=ENDPOINTS_MENU)

AGENT_NAME = "humidity_agent"
PORT = 5003
DATA_LOG_PATH = "/app/agents/humidity_agent/humidity_agent_data_log.json"
intelligence_path = "/app/agents/humidity_agent/humidity_agent_intelligence.json"

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

    registry_path = "/app/agents/humidity_agent/created_intelligence.json"

    if not os.path.exists(registry_path):
        return jsonify([])

    with open(registry_path, "r") as f:
        registry = json.load(f)

    result = []

    for intel in registry:

        result_path = intel.get("result_path")

        if not result_path:
            continue

        abs_path = os.path.join(
            "/app/agents/humidity_agent",
            result_path
        )

        if not os.path.exists(abs_path):
            continue

        try:
            with open(abs_path, "r") as rf:
                data = json.load(rf)

            result.append({
                "intelligence_id": (
                    intel.get("intelligence_id")
                    or intel.get("uuid")
                ),
                "intelligence_name": intel.get("intelligence_name"),
                "data": data
            })

        except Exception:
            pass

    return jsonify(result)

@app.route("/intelligence/<intelligence_id>")
def intelligence_by_id(intelligence_id):

    with open(
        "/app/agents/humidity_agent/created_intelligence.json",
        "r"
    ) as f:
        registry = json.load(f)

    for intel in registry:

        current_id = (
            intel.get("intelligence_id")
            or intel.get("uuid")
        )

        if current_id == intelligence_id:

            result_path = intel.get("result_path")

            abs_path = os.path.join(
                "/app/agents/humidity_agent",
                result_path
            )

            with open(abs_path, "r") as rf:
                return jsonify(json.load(rf))

    return jsonify({
        "error": "Not found"
    }), 404

@app.route("/intelligence/<intelligence_id>/<key>")
def intelligence_value_by_id(intelligence_id, key):

    with open(
        "/app/agents/humidity_agent/created_intelligence.json",
        "r"
    ) as f:
        registry = json.load(f)

    for intel in registry:

        current_id = (
            intel.get("intelligence_id")
            or intel.get("uuid")
        )

        if current_id == intelligence_id:

            result_path = intel.get("result_path")

            abs_path = os.path.join(
                "/app/agents/humidity_agent",
                result_path
            )

            if not os.path.exists(abs_path):
                return jsonify({
                    "error": "Result file not found"
                }), 404

            with open(abs_path, "r") as rf:
                data = json.load(rf)

            # top level key
            if key in data:
                return jsonify({
                    key: data[key]
                })

            # nested key
            for value in data.values():

                if isinstance(value, dict) and key in value:

                    return jsonify({
                        key: value[key]
                    })

            return jsonify({
                "error": f"Key '{key}' not found"
            }), 404

    return jsonify({
        "error": "Intelligence not found"
    }), 404

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

    engine = request.form.get("engine", "").strip()

    extension = file.filename.rsplit(".", 1)[-1].lower()

    allowed_extensions = {
        "python": ["py"],
        "node": ["js"],
        "java": ["java"]
    }

    if extension not in allowed_extensions.get(engine, []):

        return jsonify({
            "status": "error",
            "message":
                f"File extension .{extension} does not match runtime engine '{engine}'"
        }), 400
    
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
    
    intel_path = f"/app/agents/humidity_agent/intel_definitions"
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
    
    intel_path = f"/app/agents/humidity_agent/intel_definitions"
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
            "next_steps": "Restart the humidity_intelligence_service to apply changes"
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error deleting file: {str(e)}"
        }), 500

# -------- Main Flow -------- #
if __name__ == "__main__":
    import time
    time.sleep(5)

    register_with_controller()
    register_with_consul()
    save_metadata_to_json(metadata, metadata_path)
    app.run(host="0.0.0.0", port=5003)
