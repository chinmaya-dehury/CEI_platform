import os
import json
from datetime import datetime, timedelta
from flask import jsonify, request

def get_requirements_data(data_log_path, agent_name, unit, requirement="average_humidity", duration=5):
    try:
        if not os.path.exists(data_log_path):
            return jsonify({"error": "No data log found"}), 404

        with open(data_log_path) as f:
            records = json.load(f)

        # If called from POST, override requirement & duration from request JSON
        if request.method == 'POST':
            req_data = request.get_json()
            if not req_data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            requirement = req_data.get("requirement", requirement)
            duration = int(req_data.get("duration_minutes", duration))

        cutoff = datetime.utcnow() - timedelta(minutes=duration)
        recent = [r["humidity"] for r in records if datetime.fromisoformat(r["timestamp"]) > cutoff]

        if not recent:
            return jsonify({"response": f"No recent data in last {duration} minutes"}), 200

        if requirement == "average_humidity":
            value = round(sum(recent) / len(recent), 2)
        elif requirement == "min_humidity":
            value = min(recent)
        elif requirement == "max_humidity":
            value = max(recent)
        else:
            return jsonify({"error": f"Unknown requirement: {requirement}"}), 400

        return jsonify({
            "agent": agent_name,
            "requirement": requirement,
            "value": value,
            "unit": unit,
            "data_points_considered": len(recent)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
