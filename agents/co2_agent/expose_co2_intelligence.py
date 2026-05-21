import json
from flask import Flask, jsonify

INTELLIGENCE_PATH = "/data/co2_intelligence.json"

app = Flask(__name__)

@app.route('/intelligence')
def expose_intelligence():
    try:
        with open(INTELLIGENCE_PATH) as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5002, debug=True)
