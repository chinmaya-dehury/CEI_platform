import requests

CONSUL_URL = "http://consul:8500"  # Use container name, not localhost

def get_registered_agents():
    agents = []
    try:
        # Get all registered services
        response = requests.get(f"{CONSUL_URL}/v1/catalog/services")
        response.raise_for_status()

        services = response.json()

        for service in services:
            if "agent" in service:
                try:
                    detail_response = requests.get(f"{CONSUL_URL}/v1/catalog/service/{service}")
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
                    print(f"Error fetching details for {service}: {e}")
    except requests.RequestException as e:
        print(f"Error connecting to Consul: {e}")
    except ValueError as e:
        print(f"Error decoding JSON from Consul: {e}")

    return agents





