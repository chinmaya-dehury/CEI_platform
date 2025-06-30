from flask import Flask, render_template, jsonify, Response
from consul_utils import get_registered_agents
from agent_utils import fetch_intelligence, fetch_health, fetch_requirements
import json
import os
import io
import csv

app = Flask(__name__)

@app.route('/')
def index():
    agents = get_registered_agents()
    health_data = fetch_health()
    requirements_data = fetch_requirements()  # fetch requirements along with health

    # Attach health and requirements data to each agent for rendering
    for agent in agents:
        agent_id = agent['ID']
        agent["Health"] = health_data.get(agent_id, {}).get("status", "unknown")
        agent["Requirements"] = json.dumps(requirements_data.get(agent_id, {}), indent=2)  # pretty JSON

    return render_template("dashboard.html", agents=agents)

@app.route('/intelligence')
def intelligence():
    all_data = fetch_intelligence()
    return jsonify(all_data)

@app.route('/requirements')
def requirements():
    requirements_data = fetch_requirements()
    return jsonify(requirements_data)

@app.route('/data/export/json')
def export_json():
    data = {
        "intelligence": fetch_intelligence(),
    }
    return jsonify(data)

@app.route('/data/export/csv')
def export_csv():
    intelligence_data = fetch_intelligence()

    # Create a CSV stream in memory
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['agent_id', 'timestamp', 'value'])  # CSV headers

    for agent_id, log in intelligence_data.items():
        if isinstance(log, dict) and "error" not in log:
            timestamp = log.get("timestamp", "N/A")

            # Priority-ordered fields we care about
            possible_keys = [
                "average_vehicle_count",
                "average_humidity",
                "average_co2",
                "noise_level",
                "average_temperature"
                # Add more fields if needed
            ]

            # Find the first existing field in the log
            value = next((log[key] for key in possible_keys if key in log), "N/A")
        else:
            timestamp = "N/A"
            value = "N/A"

        cw.writerow([agent_id, timestamp, value])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=intelligence_data.csv"}
    )

if __name__ == '__main__':
    os.environ['FLASK_ENV'] = 'development'
    app.run(debug=True, host="0.0.0.0", port=8000)
