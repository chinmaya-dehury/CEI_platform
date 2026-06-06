import os
import uuid
import importlib

from flask import Flask,json, jsonify


app = Flask(__name__)

INTELLIGENCE_FOLDER = "agents.noise_agent.intel_definitions"

_DOCKER_FOLDER = "agents/noise_agent/intel_definitions"
_LOCAL_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "intel_definitions",
)
FOLDER_PATH = _DOCKER_FOLDER if os.path.isdir(_DOCKER_FOLDER) else _LOCAL_FOLDER

AGENT_BASE_PATH = os.path.dirname(FOLDER_PATH)


intelligence_registry = []

def load_created_intelligence_registry():
    """Load user-uploaded intelligence entries with .data file contents."""
    registry_path = os.path.join(AGENT_BASE_PATH, "created_intelligence.json")
    if not os.path.exists(registry_path):
        return []

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read created_intelligence.json: {e}")
        return []

    seen = {}
    for entry in registry:
        name = entry.get("intelligence_name")
        if not name:
            continue
        if not entry.get("intelligence_id"):
            entry["intelligence_id"] = entry.get("uuid")

        result_path = entry.get("result_path", "")
        if result_path:
            if result_path.startswith("/app/agents/noise_agent/"):
                abs_result = result_path
            elif result_path.startswith("agents/noise_agent/"):
                abs_result = os.path.join(
                    os.path.dirname(os.path.dirname(AGENT_BASE_PATH)),
                    result_path,
                )
            else:
                abs_result = os.path.join(AGENT_BASE_PATH, result_path)

            if os.path.exists(abs_result):
                try:
                    with open(abs_result, "r", encoding="utf-8") as rf:
                        content = rf.read().strip()
                        entry["result_data"] = json.loads(content) if content else {}
                except Exception as ex:
                    entry["result_data"] = {"error": str(ex)}
            else:
                entry.setdefault("result_data", {"error": "Result file not found"})

        if not entry.get("execution_data") and entry.get("result_data"):
            entry["execution_data"] = entry["result_data"]

        metadata_path = os.path.join(FOLDER_PATH, f"{name}_metadata.json")
        if os.path.isfile(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as mf:
                    metadata = json.load(mf)
                meta_install = metadata.get("engine_installation")
                reg_install = entry.get("engine_installation") or {}
                if meta_install and (
                    reg_install.get("status") == "pending"
                    or (
                        meta_install.get("installed")
                        and not reg_install.get("installed")
                    )
                ):
                    entry["engine_installation"] = meta_install
            except Exception:
                pass

        seen[name] = entry
    return list(seen.values())

def load_intelligences():

    for file in os.listdir(FOLDER_PATH):

        if file.endswith(".py") and file != "__init__.py":

            module_name = file[:-3]

            full_module = f"{INTELLIGENCE_FOLDER}.{module_name}"

            module = importlib.import_module(full_module)

            if hasattr(module, "INTELLIGENCE_INFO"):

                info = module.INTELLIGENCE_INFO.copy()

                function_name = info["function_name"]

                sample_data = info["sample_data"]

                intelligence_function = getattr(
                    module,
                    function_name
                )

                intelligence_output = intelligence_function(
                    sample_data
                )

                registry_item = {

                    "intelligence_id": str(uuid.uuid4()),

                    "intelligence_name":
                        info["intelligence_name"],

                    "description":
                        info["description"],

                    "category":
                        info["category"],

                    "intelligence_data":
                        intelligence_output
                }

                intelligence_registry.append(
                    registry_item
                )


load_intelligences()


@app.route("/intelligence", methods=["GET"])
def get_intelligence():

    created = load_created_intelligence_registry()

    return jsonify({

        "agent_name": "noise_agent",

        "intelligence": intelligence_registry,

        "created_intelligence": created

    })


@app.route("/")
def home():

    return jsonify({
        "message": "Noise Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5010)