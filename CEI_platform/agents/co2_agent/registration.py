import os
import json
import socket
import requests
import http.client

UUID_PATH = "/data/co2_agent_metadata.json"
CONTROLLER_URL = "http://controller:9000/register"

def save_metadata(metadata):
    """
    Save metadata with UUID to disk.
    """
    os.makedirs(os.path.dirname(UUID_PATH), exist_ok=True)
    with open(UUID_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[INFO] Saved metadata with UUID: {metadata.get('uuid')}")

def load_metadata(metadata):
    """
    Load metadata (including UUID) from disk, updating the given metadata dict.
    Returns True if successful, False otherwise.
    """
    if os.path.exists(UUID_PATH):
        with open(UUID_PATH) as f:
            metadata.update(json.load(f))
        print(f"[INFO] Loaded metadata with UUID: {metadata['uuid']}")
        return True
    return False

def register_with_controller(metadata):
    """
    Register agent with controller and obtain UUID. Updates metadata in-place.
    """
    try:
        response = requests.post(CONTROLLER_URL, json=metadata)
        if response.status_code == 200:
            metadata["uuid"] = response.json().get("uuid")
            print(f"[INFO] UUID received from controller: {metadata['uuid']}")
            save_metadata(metadata)
        else:
            print(f"[ERROR] Failed to register with controller: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[ERROR] Controller registration failed: {e}")

def register_with_consul(metadata, port):
    """
    Register agent with Consul service discovery using metadata and agent port.
    """
    try:
        agent_ip = socket.gethostbyname(socket.gethostname())  # Container IP

        service = {
            "ID": metadata["uuid"],
            "Name": metadata["agent_name"],
            "Address": agent_ip,
            "Port": port,
            "Meta": {
                "sensor_type": metadata["sensor_type"],
                "location": metadata["location"],
                "unit": metadata["unit"],
                "frequency": metadata["frequency"]
            },
            "Check": {
                "HTTP": f"http://{agent_ip}:{5001}/health",
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
