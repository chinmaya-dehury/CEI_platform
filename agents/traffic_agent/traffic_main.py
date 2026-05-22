import uuid

from flask import Flask, jsonify

from agents.traffic_agent.intel_definitions.traffic_alert import detect_traffic_congestion

from agents.traffic_agent.intel_definitions.traffic_trend import analyze_traffic_trend

from agents.traffic_agent.intel_definitions.calculate_average_traffic import calculate_average_traffic

from agents.traffic_agent.intel_definitions.classify_traffic_level import classify_traffic_level


app = Flask(__name__)


intelligence_registry = [

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Traffic Congestion Intelligence",
        "description": "Detects heavy traffic congestion",
        "category": "transport",
        "intelligence_data" : detect_traffic_congestion(80)  # Example value for traffic density    
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Traffic Trend Intelligence",
        "description": "Analyzes long term traffic trends",
        "category": "analytics",
        "intelligence_data" : analyze_traffic_trend([50, 60, 70, 80])  # Example traffic data
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Traffic Average Analysis",
        "description": "Calculates average traffic density",
        "category": "statistics",
        "intelligence_data" : calculate_average_traffic([50, 60, 70, 80])  # Example traffic data
    },

    {
        "intelligence_id": str(uuid.uuid4()),
        "intelligence_name": "Traffic Level Classification",
        "description": "Classifies road traffic conditions",
        "category": "transport",
        "intelligence_data" : classify_traffic_level(80)  # Example value for traffic density
    }

]


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    return jsonify({

        "agent_name": "traffic_agent",

        "intelligence": intelligence_registry

    })


@app.route("/")
def home():

    return jsonify({
        "message": "Traffic Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5014)