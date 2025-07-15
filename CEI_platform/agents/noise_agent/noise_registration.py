import os
import json
import requests
import socket
import http.client

AGENT_NAME = "noise_agent"
PORT = 5002
UUID_PATH = "/agents/noise_agent/noise_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"

# -------- Metadata -------- #
metadata = {
    "uuid": "",
    "sensor_type": "Noise Sensor",
    "frequency": "Every 10 seconds",
    "unit": "dB",
    "location": "Zone C",
    "data_name": "noise_level",
    "agent_name": AGENT_NAME
}

def save_metadata():
    os.makedirs(os.path.dirname(UUID_PATH), exist_ok=True)
    with open(UUID_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

def load_metadata():
    if os.path.exists(UUID_PATH):
        with open(UUID_PATH) as f:
            metadata.update(json.load(f))
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
        agent_ip = socket.gethostbyname(socket.gethostname())
        print(f"[INFO] Resolved agent IP: {agent_ip}")

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_ip,
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
        conn.request(
            "PUT",
            "/v1/agent/service/register",
            body=json.dumps(service),
            headers={"Content-Type": "application/json"}
        )
        res = conn.getresponse()
        print(f"[INFO] Registered with Consul. Status: {res.status} {res.reason}")
        conn.close()

    except Exception as e:
        print(f"[ERROR] Consul registration exception: {e}")
