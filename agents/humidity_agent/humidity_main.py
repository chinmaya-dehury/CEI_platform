import uuid

from flask import Flask, jsonify

from agents.humidity_agent.intel_definitions.humidity_alert import detect_abnormal_humidity

from agents.humidity_agent.intel_definitions.humidity_trend import analyze_humidity_trend

from agents.humidity_agent.intel_definitions.calculate_average_humidity import calculate_average_humidity

from agents.humidity_agent.intel_definitions.classify_humidity_level import classify_humidity_level


app = Flask(__name__)


intelligence_registry = [

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Humidity Alert Intelligence",
        "description": "Detects abnormal humidity increase",
        "category": "environment",
        "intelligence_data" : detect_abnormal_humidity(85)  # Example value
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Humidity Trend Intelligence",
        "description": "Analyzes long term humidity trends",
        "category": "analytics",
        "intelligence_data": analyze_humidity_trend([60, 62, 65, 70, 75])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Humidity Average Analysis",
        "description": "Calculates average humidity levels",
        "category": "statistics",
        "intelligence_data": calculate_average_humidity([60, 62, 65, 70, 75])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Humidity Level Classification",
        "description": "Classifies humidity condition levels",
        "category": "environment",
        "intelligence_data": classify_humidity_level(85)  # Example value
    }

]


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    return jsonify({

        "agent_name": "humidity_agent",

        "intelligence": intelligence_registry

    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5011)