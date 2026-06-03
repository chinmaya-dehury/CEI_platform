from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json
import os
import uuid

app = Flask(__name__)

REGISTRATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registrations.json")


def load_registrations():
    if not os.path.exists(REGISTRATIONS_FILE):
        return []

    try:
        with open(REGISTRATIONS_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_registrations(registrations):
    with open(REGISTRATIONS_FILE, "w") as f:
        json.dump(registrations, f, indent=2)


def create_registration(data):
    new_uuid = str(uuid.uuid4())
    agent_name = data.get("agent_name") or data.get("name") or "unknown_agent"

    registration = {
        "uuid": new_uuid,
        "intelligence_id": new_uuid,
        "agent_name": agent_name,
        "sensor_type": data.get("sensor_type", ""),
        "location": data.get("location", ""),
        "unit": data.get("unit", ""),
        "frequency": data.get("frequency", ""),
        "data_name": data.get("data_name", ""),
        "registered_at": datetime.utcnow().isoformat(),
        "metadata": data
    }

    registrations = load_registrations()
    existing = next(
        (
            r for r in registrations
            if r.get("agent_name") == agent_name
            and r.get("metadata", {}).get("name") == data.get("name")
            and r.get("metadata", {}).get("data_name") == data.get("data_name")
        ),
        None
    )

    if existing:
        if "intelligence_id" not in existing:
            existing["intelligence_id"] = existing.get("uuid")

            save_registrations(registrations)

        return existing

    registrations.append(registration)
    save_registrations(registrations)
    

    print(f"Received registration from {agent_name}, assigning UUID: {new_uuid}")
    return registration


@app.route("/", methods=["GET"])
def index():
    return render_template("controller.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    registration = create_registration(data or {})

    if request.is_json:
        return jsonify({
            "uuid": registration["uuid"],
            "intelligence_id": registration["intelligence_id"],
            "address": registration["agent_name"],
            "registration": registration
        })

    return jsonify({
        "uuid": registration["uuid"],
        "intelligence_id": registration["intelligence_id"],
        "address": registration["agent_name"],
        "registration": registration
    })


@app.route("/registrations", methods=["GET"])
def registrations():
    return jsonify(load_registrations())

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
