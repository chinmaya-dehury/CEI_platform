import os
import sys
import uuid
import importlib
import json
import inspect
import traceback

from flask import Flask, jsonify


app = Flask(__name__)


INTELLIGENCE_FOLDER = "agents.co2_agent.intel_definitions"

_DOCKER_FOLDER = "agents/co2_agent/intel_definitions"
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
            if result_path.startswith("/app/agents/co2_agent/"):
                abs_result = result_path
            elif result_path.startswith("agents/co2_agent/"):
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
    """Load all intelligence modules and auto-discover functions."""
    global intelligence_registry
    intelligence_registry = []

    if not os.path.isdir(FOLDER_PATH):
        print(f"[WARN] Intelligence folder not found: {FOLDER_PATH}")
        return

    skip_files = {
        "__init__.py",
        "weather_api_client.py",
        "intelligence_upload_handler.py",
        "EXAMPLE_TEMPLATE.py",
    }

    for file in os.listdir(FOLDER_PATH):
        if not file.endswith(".py") or file in skip_files:
            continue

        module_name = file[:-3]
        full_module = f"{INTELLIGENCE_FOLDER}.{module_name}"

        try:
            if full_module in sys.modules:
                module = importlib.reload(sys.modules[full_module])
            else:
                module = importlib.import_module(full_module)

            metadata_path = os.path.join(FOLDER_PATH, f"{module_name}_metadata.json")

            if os.path.exists(metadata_path):
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "intelligence_id": str(uuid.uuid4()),
                    "filename": file,
                    "module_name": module_name,
                    "status": "loaded",
                }

            data_path = os.path.join(FOLDER_PATH, f"{module_name}.data")
            intelligence_data = {}
            if os.path.exists(data_path):
                try:
                    with open(data_path, "r", encoding="utf-8") as df:
                        intelligence_data = json.load(df)
                except Exception:
                    intelligence_data = {}

            for func_name, func_obj in inspect.getmembers(module, inspect.isfunction):
                if func_name.startswith("_"):
                    continue

                try:
                    functions_meta = metadata.get("functions", [])
                    if isinstance(functions_meta, list) and functions_meta:
                        if isinstance(functions_meta[0], dict):
                            func_description = next(
                                (
                                    f.get("description", f"Intelligence function: {func_name}")
                                    for f in functions_meta
                                    if f.get("name") == func_name
                                ),
                                f"Intelligence function: {func_name}",
                            )
                        else:
                            func_description = (
                                inspect.getdoc(func_obj)
                                or f"Intelligence function: {func_name}"
                            )
                    else:
                        func_description = (
                            inspect.getdoc(func_obj)
                            or f"Intelligence function: {func_name}"
                        )

                    try:
                        result = func_obj(use_api=True)
                    except TypeError:
                        result = func_obj()

                    intelligence_registry.append(
                        {
                            "intelligence_id": metadata.get(
                                "intelligence_id", str(uuid.uuid4())
                            ),
                            "intelligence_name": module_name,
                            "function_name": func_name,
                            "module": module_name,
                            "description": func_description[:200],
                            "intelligence_data": result,
                            "data_file": f"intel_definitions/{module_name}.data",
                            "implementation_path": (
                                f"agents/co2_agent/intel_definitions/{file}"
                            ),
                            "metadata_file": metadata_path
                            if os.path.exists(metadata_path)
                            else None,
                            "stored_data": intelligence_data,
                        }
                    )

                    print(
                        f"[INFO] Loaded intelligence: {func_name} from {module_name}"
                    )

                except Exception as e:
                    print(
                        f"[ERROR] Failed to execute function {func_name} "
                        f"from {module_name}: {e}"
                    )
                    continue

            

        except Exception as e:
            print(f"[ERROR] Failed to load intelligence from {module_name}")
            traceback.print_exc()
            continue


@app.route("/intelligence", methods=["GET"])
def get_intelligence():
    load_intelligences()
    created = load_created_intelligence_registry()

    return jsonify(
        {
            "agent_name": "co2_agent",
            "intelligence": intelligence_registry,
            "created_intelligence": created,
        }
    )


@app.route("/")
def home():
    return jsonify({"message": "CO2 Intelligence Service Running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010)
