import uuid

from flask import Flask, jsonify

from agents.noise_agent.intel_definitions.noise_alert import detect_abnormal_noise

from agents.noise_agent.intel_definitions.noise_trend import analyze_noise_trend

from agents.noise_agent.intel_definitions.calculate_average_noise import calculate_average_noise

from agents.noise_agent.intel_definitions.classify_noise_level import classify_noise_level


app = Flask(__name__)


intelligence_registry = [

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Noise Alert Intelligence",
        "description": "Detects abnormal noise increase",
        "category": "environment",
        "intelligence_data" : detect_abnormal_noise(85)  # Example value
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Noise Trend Intelligence",
        "description": "Analyzes long term noise trends",
        "category": "analytics",
        "intelligence_data": analyze_noise_trend([60, 62, 65, 70, 75])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Noise Average Analysis",
        "description": "Calculates average noise levels",
        "category": "statistics",
        "intelligence_data": calculate_average_noise([60, 62, 65, 70, 75])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Noise Level Classification",
        "description": "Classifies environmental noise levels",
        "category": "environment",
        "intelligence_data": classify_noise_level(85)  # Example value
    }

]


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    return jsonify({

        "agent_name": "noise_agent",

        "intelligence": intelligence_registry

    })


@app.route("/")
def home():

    return jsonify({
        "message": "Noise Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5012)