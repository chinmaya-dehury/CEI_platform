from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    new_uuid = str(uuid.uuid4())
    print(f"Received registration from {data.get('agent_name')}, assigning UUID: {new_uuid}")
    return jsonify({"uuid": new_uuid})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
