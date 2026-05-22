import requests


INTELLIGENCE_SERVICES = [

    (
        "co2_agent",
        "http://co2_intelligence_service:5010/intelligence"
    ),

    (
        "humidity_agent",
        "http://humidity_intelligence_service:5011/intelligence"
    ),

    (
        "noise_agent",
        "http://noise_intelligence_service:5012/intelligence"
    ),

    (
        "temperature_agent",
        "http://temperature_intelligence_service:5013/intelligence"
    ),

    (
        "traffic_agent",
        "http://traffic_intelligence_service:5014/intelligence"
    )

]


def collect_repository():

    repository = []

    for agent_name, url in INTELLIGENCE_SERVICES:

        try:

            response = requests.get(url, timeout=3)

            if response.status_code == 200:

                repository.append(response.json())

            else:

                repository.append({
                    "agent_name": agent_name,
                    "error": "Service unavailable"
                })

        except Exception as e:

            repository.append({
                "agent_name": agent_name,
                "error": str(e)
            })

    return repository