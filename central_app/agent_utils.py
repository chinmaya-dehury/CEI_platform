import requests
from consul_utils import get_registered_agents

def resolve_agent_address(agent):
    agent_address = agent["Address"]
    if agent_address == "127.0.0.1":
        agent_address = agent["Name"]  # assumes agent Name == container DNS name
    return agent_address


def fetch_intelligence(agent_id=None):
    data = {}
    agents = get_registered_agents()

    for agent in agents:
        if agent_id and agent['ID'] != agent_id:
            continue

        agent_address = resolve_agent_address(agent)

        try:
            url = f"http://{agent_address}:{agent['Port']}/intelligence"
            resp = requests.get(url, timeout=2).json()
            data[agent['ID']] = resp
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch intelligence from {agent_address}:{agent['Port']}: {e}")
            data[agent['ID']] = {"error": f"Failed to fetch: {str(e)}"}
        except Exception as e:
            print(f"[ERROR] Unexpected error fetching intelligence: {e}")
            data[agent['ID']] = {"error": f"Unexpected error: {str(e)}"}
    return data


def fetch_health(agent_id=None):
    data = {}
    agents = get_registered_agents()

    for agent in agents:
        if agent_id and agent['ID'] != agent_id:
            continue

        agent_address = resolve_agent_address(agent)

        try:
            url = f"http://{agent_address}:{agent['Port']}/health"
            resp = requests.get(url, timeout=2).json()
            data[agent['ID']] = resp
        except requests.RequestException as e:
            print(f"[ERROR] Health check failed for {agent_address}:{agent['Port']}: {e}")
            data[agent['ID']] = {"status": "unreachable", "error": str(e)}
        except Exception as e:
            print(f"[ERROR] Unexpected error checking health: {e}")
            data[agent['ID']] = {"status": "unreachable", "error": str(e)}
    return data


def fetch_requirements(agent_id=None):
    data = {}
    agents = get_registered_agents()

    for agent in agents:
        if agent_id and agent['ID'] != agent_id:
            continue

        agent_address = resolve_agent_address(agent)

        try:
            url = f"http://{agent_address}:{agent['Port']}/requirements"
            resp = requests.get(url, timeout=2).json()
            data[agent['ID']] = resp
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch requirements from {agent_address}:{agent['Port']}: {e}")
            data[agent['ID']] = {"error": f"Failed to fetch: {str(e)}"}
        except Exception as e:
            print(f"[ERROR] Unexpected error fetching requirements: {e}")
            data[agent['ID']] = {"error": f"Unexpected error: {str(e)}"}
    return data
