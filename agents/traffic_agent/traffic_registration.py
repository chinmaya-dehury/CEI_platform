import os
import json
import requests
import socket
import http.client

AGENT_NAME = "traffic_agent"
PORT = 5000
UUID_PATH = "/agents/traffic_agent/traffic_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"

metadata = {
    "uuid": "",
    "sensor_type": "Traffic Congestion Sensor",
    "frequency": "Every 10 seconds",
    "unit": "%",
    "location": "Junction A1",
    "data_name": "congestion_level",
    "agent_name": AGENT_NAME
}

def save_metadata():
    os.makedirs(os.path.dirname(UUID_PATH), exist_ok=True)
    with open(UUID_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

def load_metadata():
    if os.path.exists(UUID_PATH):
        with open(UUID_PATH) as f:
            loaded = json.load(f)
            metadata.update(loaded)
        print(f"[INFO] Loaded metadata and UUID: {metadata['uuid']}")
        return True
    return False

def register_with_controller():
    try:
        response = requests.post(CONTROLLER_URL, json=metadata)
        if response.status_code == 200:
            metadata["uuid"] = response.json().get("uuid")
            print(f"[INFO] UUID received from controller: {metadata['uuid']}")
            save_metadata()
        else:
            print(f"[ERROR] Failed to register with controller: {response.text}")
    except Exception as e:
        print(f"[ERROR] Controller registration exception: {e}")

def register_with_consul():
    try:
        # Use Docker's container hostname/service name if provided, fallback to system hostname
        agent_ip = os.environ.get('AGENT_HOSTNAME', socket.gethostname())
        print(f"[INFO] Registering agent using address: {agent_ip}")

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_ip,   # IMPORTANT: Should be a *Docker service/container name*, NOT 127.0.0.1!
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{agent_ip}:{PORT}/health",
                "Interval": "10s"
            }
        }

        conn = http.client.HTTPConnection("consul", 8500)
        conn.request("PUT", "/v1/agent/service/register", body=json.dumps(service),
                    headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        print(f"[INFO] Registered with Consul. Status: {res.status} {res.reason}")
        conn.close()
    except Exception as e:
        print(f"[ERROR] Consul registration exception: {e}")
