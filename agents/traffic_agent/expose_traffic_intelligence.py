from flask import Flask, jsonify
import json
import os

# Path to your intelligence JSON file (should match where your agent writes it)
INTELLIGENCE_PATH = "/data/traffic_intelligence.json"

app = Flask(__name__)

@app.route('/intelligence', methods=['GET'])
def expose_intelligence():
    if not os.path.isfile(INTELLIGENCE_PATH):
        return jsonify({"error": "No intelligence data found. Generate it first."}), 404
    try:
        with open(INTELLIGENCE_PATH, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to read intelligence data: {str(e)}"}), 500

if __name__ == "__main__":
    # You can change the port if you want
    app.run(host="0.0.0.0", port=5000, debug=True)
