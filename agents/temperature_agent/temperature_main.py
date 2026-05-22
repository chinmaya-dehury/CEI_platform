import uuid

from flask import Flask, jsonify

from agents.temperature_agent.intel_definitions.temperature_alert import detect_abnormal_temperature

from agents.temperature_agent.intel_definitions.temperature_trend import analyze_temperature_trend

from agents.temperature_agent.intel_definitions.calculate_average_temperature import calculate_average_temperature

from agents.temperature_agent.intel_definitions.classify_temperature_level import classify_temperature_level


app = Flask(__name__)


intelligence_registry = [

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Temperature Alert Intelligence",
        "description": "Detects abnormal temperature increase",
        "category": "environment",
        "intelligence_data" : detect_abnormal_temperature(35)  # Example value
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Temperature Trend Intelligence",
        "description": "Analyzes long term temperature trends",
        "category": "analytics",
        "intelligence_data": analyze_temperature_trend([20, 22, 25, 30, 35])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Temperature Average Analysis",
        "description": "Calculates average temperature values",
        "category": "statistics",
        "intelligence_data": calculate_average_temperature([20, 22, 25, 30, 35])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Temperature Level Classification",
        "description": "Classifies environmental temperature conditions",
        "category": "environment",
        "intelligence_data": classify_temperature_level(35)  # Example value    
    }

]


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    return jsonify({

        "agent_name": "temperature_agent",

        "intelligence": intelligence_registry

    })


@app.route("/")
def home():

    return jsonify({
        "message": "Temperature Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5013)