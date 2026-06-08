"""
Repository Service

This module collects and aggregates intelligence information from all agents.
It retrieves intelligence data either directly from agent intelligence services
or from locally stored registry files when services are unavailable.

Key Responsibilities:
- Fetch intelligence information from agent intelligence services.
- Read created_intelligence.json registry files.
- Resolve and load intelligence result (.data) files.
- Read intelligence metadata files when needed.
- Merge registry, metadata, and execution results into a unified structure.
- Provide repository data for display in the central dashboard and repository UI.
- Support fallback data retrieval when agent services are offline.

Its purpose is to discover, read, and aggregate intelligence artifacts that already exist.
"""

import requests
import os
import re
import json


INTELLIGENCE_SERVICES = [
    ("co2_agent", "http://co2_intelligence_service:5010/intelligence", 5001),
    ("humidity_agent", "http://humidity_intelligence_service:5010/intelligence", 5003),
    ("noise_agent", "http://noise_intelligence_service:5010/intelligence", 5002),
    ("temperature_agent", "http://temperature_intelligence_service:5010/intelligence", 5004),
    ("traffic_agent", "http://traffic_intelligence_service:5010/intelligence", 5000)
]

AGENTS_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")


def sanitize_name(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'^[^a-z]', 'i_', name)
    return name



def get_created_intelligence(agent_name):

    try:

        registry_path = os.path.join(
            AGENTS_BASE_PATH,
            agent_name,
            "created_intelligence.json"
        )

        if not os.path.exists(registry_path):

            return []

        with open(
            registry_path,
            "r",
            encoding="utf-8"
        ) as f:

            registry = json.load(f)

        for intel in registry:
            if not intel.get("intelligence_id"):
                intel["intelligence_id"] = intel.get("uuid")

            if not intel.get("extension"):
                impl = intel.get("implementation_path", "")
                if impl.endswith(".py"):
                    intel["extension"] = "py"
                elif "." in impl:
                    intel["extension"] = impl.rsplit(".", 1)[-1].lower()
                else:
                    intel["extension"] = "py"

            result_path = intel.get("result_path")

            if result_path:

                if result_path.startswith("agents/"):
                    abs_result_path = os.path.join(
                        os.path.dirname(AGENTS_BASE_PATH),
                        result_path,
                    )
                elif result_path.startswith("/app/"):
                    rel = result_path.split(f"/app/agents/{agent_name}/")[-1]
                    abs_result_path = os.path.join(
                        AGENTS_BASE_PATH,
                        agent_name,
                        rel,
                    )
                else:
                    abs_result_path = os.path.join(
                        AGENTS_BASE_PATH,
                        agent_name,
                        result_path,
                    )

                # #region agent log
                try:
                    _log_path = os.path.join(
                        os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))
                        ),
                        "debug-552a44.log",
                    )
                    with open(_log_path, "a", encoding="utf-8") as _lf:
                        _lf.write(
                            json.dumps(
                                {
                                    "sessionId": "552a44",
                                    "location": "repository_service.py:get_created",
                                    "message": "result path resolve",
                                    "data": {
                                        "result_path": result_path,
                                        "abs_result_path": abs_result_path,
                                        "exists": os.path.exists(abs_result_path),
                                    },
                                    "timestamp": int(__import__("time").time() * 1000),
                                    "hypothesisId": "E",
                                }
                            )
                            + "\n"
                        )
                except Exception:
                    pass
                # #endregion

                if os.path.exists(abs_result_path):

                    try:

                        with open(
                            abs_result_path,
                            "r",
                            encoding="utf-8"
                        ) as rf:

                            content = rf.read().strip()

                            if content:

                                intel["result_data"] = json.loads(content)

                            else:

                                intel["result_data"] = {}

                    except Exception as e:

                        intel["result_data"] = {
                            "error": str(e)
                        }

                else:

                    intel["result_data"] = {
                        "error": "Result file not found"
                    }

            else:

                intel["result_data"] = {}

            module_name = intel.get("intelligence_name")
            if module_name:
                metadata_path = os.path.join(
                    AGENTS_BASE_PATH,
                    agent_name,
                    "intel_definitions",
                    f"{module_name}_metadata.json",
                )
                if os.path.isfile(metadata_path):
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as mf:
                            metadata = json.load(mf)
                        meta_install = metadata.get("engine_installation")
                        reg_install = intel.get("engine_installation") or {}
                        if meta_install and (
                            reg_install.get("status") == "pending"
                            or (
                                meta_install.get("installed")
                                and not reg_install.get("installed")
                            )
                        ):
                            intel["engine_installation"] = meta_install
                    except Exception:
                        pass

        return registry

    except Exception as e:

        print(f"[ERROR] Repository failed: {e}")

        return []



def collect_repository():

    repository = []

    for agent_name, url, port in INTELLIGENCE_SERVICES:

        agent_data = {
            "agent_name": agent_name,
            "port": port,
            "intelligence": [],
            "created_intelligence": []
        }

        # Fetch from intelligence service (co2_main.py and peers)
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                service_data = response.json()
                print(
                    f"{agent_name}:",
                    service_data.get("created_intelligence")
                )
                agent_data["intelligence"] = service_data.get("intelligence", [])
                created_from_service = service_data.get("created_intelligence")
                if created_from_service and len(created_from_service) > 0:
                    agent_data["created_intelligence"] = created_from_service
                else:
                    agent_data["created_intelligence"] = get_created_intelligence(
                        agent_name
                    )
            else:
                agent_data["service_error"] = "Service unavailable"
                agent_data["created_intelligence"] = get_created_intelligence(
                    agent_name
                )
        except Exception as e:
            agent_data["service_error"] = str(e)
            agent_data["created_intelligence"] = get_created_intelligence(agent_name)

        repository.append(agent_data)

    return repository