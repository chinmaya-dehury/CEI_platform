import requests

CONSUL_URL = "http://consul:8500"  # Use container name, not localhost
CONSUL_TIMEOUT = 2  # 2 second timeout for Consul requests

def get_registered_agents():
    """Get list of registered agents from Consul. Returns empty list if unavailable."""
    agents = []
    try:
        # Get all registered services with timeout
        response = requests.get(f"{CONSUL_URL}/v1/catalog/services", timeout=CONSUL_TIMEOUT)
        response.raise_for_status()

        services = response.json()

        for service in services:
            if "agent" in service:
                try:
                    detail_response = requests.get(f"{CONSUL_URL}/v1/catalog/service/{service}", timeout=CONSUL_TIMEOUT)
                    detail_response.raise_for_status()
                    details = detail_response.json()

                    for entry in details:
                        agents.append({
                            "ID": entry.get("ServiceID", "Unknown"),
                            "Name": entry.get("ServiceName", "Unknown"),
                            "Address": entry.get("Address", "Unknown"),
                            "Port": entry.get("ServicePort", "Unknown"),
                            "Location": entry.get("Node", "Unknown")
                        })

                except requests.RequestException as e:
                    print(f"[WARN] Error fetching details for {service}: {e}")
    except requests.exceptions.Timeout:
        print(f"[WARN] Consul connection timed out at {CONSUL_URL}. Using fallback agent list.")
    except requests.RequestException as e:
        print(f"[WARN] Error connecting to Consul at {CONSUL_URL}: {e}. Using fallback agent list.")
    except ValueError as e:
        print(f"[WARN] Error decoding JSON from Consul: {e}")

    return agents





