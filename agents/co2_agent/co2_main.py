import uuid

from flask import Flask, jsonify

from agents.co2_agent.intel_definitions.pollution_alert import detect_abnormal_co2

from agents.co2_agent.intel_definitions.carbon_trend import analyze_carbon_trend

from agents.co2_agent.intel_definitions.calculate_average_co2 import calculate_average_co2

from agents.co2_agent.intel_definitions.detect_air_quality_level import detect_air_quality_level


app = Flask(__name__)


intelligence_registry = [

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Pollution Alert Intelligence",
        "description": "Detects abnormal CO2 increase",
        "category": "environment",
        "intelligence_data" : detect_abnormal_co2(850)  # Example value f
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Carbon Trend Intelligence",
        "description": "Analyzes long term CO2 trends",
        "category": "analytics",
        "intelligence_data" : analyze_carbon_trend([400, 420, 450, 480, 500])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "CO2 Average Analysis",
        "description": "Calculates average CO2 levels from collected data",
        "category": "statistics",
        "intelligence_data": calculate_average_co2([400, 420, 450, 480, 500])  # Example values
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Air Quality Classification Intelligence",
        "description": "Classifies air quality based on CO2 concentration",
        "category": "environment",
        "intelligence_data": detect_air_quality_level(850)  # Example value
    }

]


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    return jsonify({

        "agent_name": "co2_agent",

        "intelligence": intelligence_registry

    })


@app.route("/")
def home():

    return jsonify({
        "message": "CO2 Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5010)