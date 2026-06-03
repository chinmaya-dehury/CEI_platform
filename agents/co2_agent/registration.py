import os
import json
import requests
import socket
import http.client

AGENT_NAME = "co2_agent"
PORT = 5001
UUID_PATH = "/agents/co2_agent/co2_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"

metadata = {
    "uuid": "",
    "sensor_type": "CO2 Sensor",
    "frequency": "Every 10 seconds",
    "unit": "ppm",
    "location": "Zone B",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "data_name": "co2_level",
    "agent_name": "co2_agent"
}

def save_metadata():
    os.makedirs(os.path.dirname(UUID_PATH), exist_ok=True)
    with open(UUID_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[INFO] Saved metadata with UUID: {metadata.get('uuid')}")

def load_metadata():
    if os.path.exists(UUID_PATH):
        with open(UUID_PATH) as f:
            metadata.update(json.load(f))
        print(f"[INFO] Loaded metadata with UUID: {metadata['uuid']}")
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
            print(f"[ERROR] Failed to register with controller: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[ERROR] Controller registration failed: {e}")

def register_with_consul():
    try:
        # Use Docker's container hostname/service name if provided, fallback to container hostname
        agent_address = os.environ.get('AGENT_HOSTNAME', socket.gethostname())
        print(f"[INFO] Registering agent with address: {agent_address}")

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_address,
            "Port": PORT,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{agent_address}:{PORT}/health",
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
        print(f"[ERROR] Failed to register with Consul: {e}")

if __name__ == "__main__":
    if not load_metadata():
        register_with_controller()
    else:
        print(f"[INFO] Already registered with UUID: {metadata['uuid']}")

    register_with_consul()  
    
