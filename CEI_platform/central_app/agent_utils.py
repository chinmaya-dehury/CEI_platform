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
            resp = requests.get(url).json()
            data[agent['ID']] = resp
        except:
            data[agent['ID']] = {"error": "Failed to fetch"}
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
        except:
            data[agent['ID']] = {"status": "unreachable"}
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
            resp = requests.get(url).json()
            data[agent['ID']] = resp
        except:
            data[agent['ID']] = {"error": "Failed to fetch"}
    return data
