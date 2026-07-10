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
import random


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMANTIC_METADATA_PATH = os.path.join(
    PROJECT_ROOT,
    "semantic_calculation",
    "intelligence_metadata.json",
)

INTELLIGENCE_SERVICES = [
    ("co2_agent", "http://co2_intelligence_service:5010/intelligence", 5001),
    ("humidity_agent", "http://humidity_intelligence_service:5010/intelligence", 5003),
    ("noise_agent", "http://noise_intelligence_service:5010/intelligence", 5002),
    ("temperature_agent", "http://temperature_intelligence_service:5010/intelligence", 5004),
    ("traffic_agent", "http://traffic_intelligence_service:5010/intelligence", 5000)
]

AGENTS_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")

AGENT_CATALOG_HINTS = {
    "traffic_agent": ["I3", "I4", "I5"],
    "temperature_agent": ["I1", "I2", "I7", "I8"],
    "humidity_agent": ["I14", "I15", "I16"],
    "noise_agent": ["I19", "I17"],
    "co2_agent": ["I1", "I6", "I9"],
}


def sanitize_name(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'^[^a-z]', 'i_', name)
    return name


def load_semantic_catalog():
    if not os.path.isfile(SEMANTIC_METADATA_PATH):
        return []

    try:
        with open(SEMANTIC_METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _tokenize(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _is_inside(child_path, parent_path):
    try:
        child_abs = os.path.abspath(child_path)
        parent_abs = os.path.abspath(parent_path)
        return os.path.commonpath([child_abs, parent_abs]) == parent_abs
    except Exception:
        return False


def resolve_artifact_path(agent_name, artifact_path):
    expected_root = os.path.join(AGENTS_BASE_PATH, agent_name)

    if not artifact_path:
        return {
            "path": "",
            "absolute_path": "",
            "exists": False,
            "location": "unknown",
        }

    if os.path.isabs(artifact_path):
        absolute_path = os.path.normpath(artifact_path)
    elif artifact_path.startswith("/app/"):
        absolute_path = os.path.normpath(
            os.path.join(
                os.path.dirname(AGENTS_BASE_PATH),
                artifact_path.lstrip("/"),
            )
        )
    elif artifact_path.startswith("agents/"):
        absolute_path = os.path.normpath(
            os.path.join(
                os.path.dirname(AGENTS_BASE_PATH),
                artifact_path,
            )
        )
    else:
        absolute_path = os.path.normpath(
            os.path.join(expected_root, artifact_path)
        )

    location = "inside" if _is_inside(absolute_path, expected_root) else "outside"

    return {
        "path": artifact_path,
        "absolute_path": absolute_path,
        "exists": os.path.exists(absolute_path),
        "location": location,
    }


def summarize_catalog_entry(entry):
    tasks = []
    for task in entry.get("tasks", [])[:2]:
        if isinstance(task, dict):
            tasks.append(
                {
                    "name": task.get("name", ""),
                    "description": task.get("description", ""),
                }
            )
        else:
            tasks.append({"name": str(task), "description": ""})

    return {
        "id": entry.get("id", ""),
        "name": entry.get("name", ""),
        "domain": entry.get("domain", ""),
        "context": entry.get("context", ""),
        "description": entry.get("description", ""),
        "tasks": tasks,
    }


def build_catalog_highlights(catalog, limit=8):
    if not catalog:
        return []

    by_domain = {}
    for entry in catalog:
        domain = entry.get("domain", "Other")
        by_domain.setdefault(domain, []).append(entry)

    domain_buckets = list(by_domain.values())
    for bucket in domain_buckets:
        random.shuffle(bucket)

    random.shuffle(domain_buckets)

    picked = []
    cursor = 0
    while len(picked) < limit and any(bucket for bucket in domain_buckets):
        bucket = domain_buckets[cursor % len(domain_buckets)]
        if bucket:
            picked.append(bucket.pop(0))
        cursor += 1
        if cursor > 1000:
            break

    return [summarize_catalog_entry(entry) for entry in picked]


def pick_catalog_matches(agent_name, intel, catalog, limit=2):
    hint_ids = AGENT_CATALOG_HINTS.get(agent_name, [])
    hinted = []
    for entry in catalog:
        if entry.get("id") in hint_ids:
            hinted.append(entry)

    if hinted:
        return [summarize_catalog_entry(entry) for entry in hinted[:limit]]

    source_text = " ".join(
        [
            intel.get("intelligence_name", ""),
            intel.get("description", ""),
            agent_name,
            intel.get("implementation_path", ""),
        ]
    )
    source_tokens = _tokenize(source_text)

    scored = []
    for entry in catalog:
        entry_text = " ".join(
            [
                entry.get("id", ""),
                entry.get("name", ""),
                entry.get("domain", ""),
                entry.get("context", ""),
                entry.get("description", ""),
                " ".join(
                    f"{task.get('name', '')} {task.get('description', '')}"
                    for task in entry.get("tasks", [])
                    if isinstance(task, dict)
                ),
            ]
        )
        entry_tokens = _tokenize(entry_text)
        score = len(source_tokens & entry_tokens)
        if agent_name.split("_")[0] in entry_text.lower():
            score += 1
        scored.append((score, entry.get("id", ""), entry))

    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen = [entry for score, _, entry in scored if score > 0][:limit]

    if not chosen:
        chosen = catalog[:limit]

    return [summarize_catalog_entry(entry) for entry in chosen]


def enrich_intelligence_entry(agent_name, intel, catalog):
    entry = dict(intel)
    entry["agent_name"] = agent_name
    entry["intelligence_id"] = entry.get("intelligence_id") or entry.get("uuid")
    entry["implementation_status"] = resolve_artifact_path(
        agent_name,
        entry.get("implementation_path", ""),
    )
    entry["result_status"] = resolve_artifact_path(
        agent_name,
        entry.get("result_path", ""),
    )
    entry["catalog_matches"] = pick_catalog_matches(agent_name, entry, catalog)
    return entry



def get_created_intelligence(agent_name, catalog=None):

    if catalog is None:
        catalog = load_semantic_catalog()

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

        return [enrich_intelligence_entry(agent_name, intel, catalog) for intel in registry]

    except Exception as e:

        print(f"[ERROR] Repository failed: {e}")

        return []



def collect_repository():

    repository = []
    semantic_catalog = load_semantic_catalog()
    catalog_highlights = build_catalog_highlights(semantic_catalog, limit=8)

    for agent_name, url, port in INTELLIGENCE_SERVICES:

        agent_data = {
            "agent_name": agent_name,
            "port": port,
            "intelligence": [],
            "created_intelligence": [],
            "catalog_highlights": catalog_highlights,
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
                    agent_data["created_intelligence"] = [
                        enrich_intelligence_entry(agent_name, intel, semantic_catalog)
                        for intel in created_from_service
                    ]
                else:
                    agent_data["created_intelligence"] = get_created_intelligence(
                        agent_name,
                        semantic_catalog,
                    )
            else:
                agent_data["service_error"] = "Service unavailable"
                agent_data["created_intelligence"] = get_created_intelligence(
                    agent_name,
                    semantic_catalog,
                )
        except Exception as e:
            agent_data["service_error"] = str(e)
            agent_data["created_intelligence"] = get_created_intelligence(
                agent_name,
                semantic_catalog,
            )

        random.shuffle(agent_data["created_intelligence"])

        repository.append(agent_data)

    random.shuffle(repository)

    return repository