from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # goes up one level from search_service/
INTELLIGENCE_DIR = os.path.join(BASE_DIR, "data")

# Mapping intelligence filenames to their agent's port
AGENT_PORTS = {
    "co2_agent_intelligence.json": "5001",
    "humidity_intelligence.json": "5003",
    "temperature_intelligence.json": "5004",
    "noise_intelligence.json": "5002",
    "traffic_intelligence.json": "5000"
}

def get_agent_url(filename):
    port = AGENT_PORTS.get(filename)
    return f"http://localhost:{port}" if port else "unknown"

def search_intelligence(requirement_key):
    results = []

    for filename in os.listdir(INTELLIGENCE_DIR):
        if filename.endswith("_intelligence.json"):
            try:
                filepath = os.path.join(INTELLIGENCE_DIR, filename)
                with open(filepath) as f:
                    intelligence = json.load(f)

                if requirement_key in intelligence:
                    results.append({
                        "value": intelligence[requirement_key],
                        "agent_id": intelligence.get("agent", "unknown"),
                        "url": get_agent_url(filename)
                    })
            except Exception as e:
                print(f"⚠️ Error reading {filename}: {e}")

    return results

@app.route("/search", methods=["GET"])
def search():
    requirement = request.args.get("requirement")
    if not requirement:
        return jsonify({"error": "Missing 'requirement' parameter"}), 400

    results = search_intelligence(requirement)
    if not results:
        return jsonify({"message": "No such intelligence available"}), 404

    return jsonify(results), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)
