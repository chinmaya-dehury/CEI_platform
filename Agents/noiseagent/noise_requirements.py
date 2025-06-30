import os
import json
from datetime import datetime, timedelta
from flask import jsonify, request

def get_requirements_data(data_log_path, agent_name, unit, requirement="average_noise", duration=5):
    try:
        if not os.path.exists(data_log_path):
            return jsonify({"error": "No data log found"}), 404

        with open(data_log_path, "r") as f:
            records = json.load(f)

        # Override requirement/duration if POST with JSON payload
        if request.method == 'POST':
            req_data = request.get_json()
            if not req_data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            requirement = req_data.get("requirement", requirement)
            duration = int(req_data.get("duration_minutes", duration))

        cutoff = datetime.utcnow() - timedelta(minutes=duration)
        recent = [
            r["noise_level"] for r in records
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            return jsonify({"response": f"No recent data in last {duration} minutes"}), 200

        if requirement == "average_noise":
            value = round(sum(recent) / len(recent), 2)
        elif requirement == "min_noise":
            value = min(recent)
        elif requirement == "max_noise":
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
