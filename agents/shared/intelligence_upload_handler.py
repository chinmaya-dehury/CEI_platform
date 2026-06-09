
"""
Intelligence Module Upload Handler
Stores uploaded intelligence, executes it using sample data,
and stores output in filename.data
"""

from fileinput import filename
from fileinput import filename
import os
import json
import re
import ast
from urllib import response
from urllib import response
import uuid
import random
import requests
import importlib
import sys
import threading

from datetime import datetime
from werkzeug.utils import secure_filename
from agents.shared.engine_installer import EngineInstaller
import io
from contextlib import redirect_stdout

class IntelligenceUploadHandler:
    ALLOWED_EXTENSIONS = {"py"}
    MAX_FILE_SIZE = 10 * 1024 * 1024 

    @staticmethod
    def get_intel_path(agent_name):
        docker_path = f"/app/agents/{agent_name}/intel_definitions"

        if os.path.isdir(docker_path):
            return docker_path

        return os.path.join(
            os.getcwd(),
            "agents",
            agent_name,
            "intel_definitions"
        )

    @staticmethod
    def get_agent_base_path(agent_name):
        return os.path.dirname(
            IntelligenceUploadHandler.get_intel_path(agent_name)
        )

    # ---------------------------------------------------
    # Validate extension
    # ---------------------------------------------------

    @staticmethod
    def allowed_file(filename):

        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower()
            in IntelligenceUploadHandler.ALLOWED_EXTENSIONS
        )

    # ---------------------------------------------------
    # Validate filename
    # ---------------------------------------------------

    @staticmethod
    def validate_filename(filename, agent_name):

        if not filename:
            return None, "Filename is empty"

        filename = secure_filename(filename)

        reserved = [

            "__init__.py",

            "intelligence_upload_handler.py"
        ]

        if filename in reserved:
            return None, f"{filename} is reserved"

        intel_path = f"/app/agents/{agent_name}/intel_definitions"

        file_path = os.path.join(
            intel_path,
            filename
        )

        if os.path.exists(file_path):
            return filename, "FILE_EXISTS"

        return filename, None

    @staticmethod
    def _load_existing_upload(secure_name,agent_name):
        """Return saved upload artifacts when the module was already created."""
        base_path = f"/app/agents/{agent_name}/intel_definitions"
        module_name = secure_name[:-3]
        file_path = os.path.join(base_path, secure_name)
        metadata_path = os.path.join(base_path, f"{module_name}_metadata.json")
        data_path = os.path.join(base_path, f"{module_name}.data")
        agent_base_path = f"/app/agents/{agent_name}"

        registry_path = os.path.join(
            agent_base_path,
            "created_intelligence.json",
        )

        if not (
            os.path.isfile(file_path)
            and os.path.isfile(metadata_path)
            and os.path.isfile(data_path)
        ):
            return None

        with open(metadata_path, "r", encoding="utf-8") as mf:
            metadata = json.load(mf)

        with open(data_path, "r", encoding="utf-8") as df:
            execution_result = json.load(df)

        registry_entry = None
        if os.path.isfile(registry_path):
            with open(registry_path, "r", encoding="utf-8") as rf:
                registry = json.load(rf)
            for entry in registry:
                if entry.get("intelligence_name") == module_name:
                    registry_entry = entry
                    break

        if registry_entry is None:
            registry_entry = {
                "uuid": metadata.get("intelligence_id"),
                "intelligence_name": module_name,
                "description": "Uploaded intelligence",
                "implementation_path": metadata.get(
                    "implementation_path",
                    f"agents/{agent_name}/intel_definitions/{secure_name}"
                ),
                "extension": "py",
                "engine": "python",
                "version": "",
                "result_path": metadata.get(
                    "result_path", f"agents/{agent_name}/intel_definitions/{module_name}.data"
                ),
                "execution_data": execution_result,
                "result_data": execution_result,
                "created_at": metadata.get("created_at"),
                "status": metadata.get("status", "active"),
            }

        IntelligenceUploadHandler._apply_metadata_engine_installation(
            registry_entry, metadata
        )

        return metadata, registry_entry, execution_result

    @staticmethod
    def _apply_metadata_engine_installation(entry, metadata):
        """Prefer finalized engine status from metadata over stale registry values."""
        meta_install = metadata.get("engine_installation")
        if not meta_install:
            return entry

        reg_install = entry.get("engine_installation") or {}
        reg_is_pending = reg_install.get("status") == "pending"
        meta_is_final = bool(meta_install.get("installed")) or meta_install.get(
            "status"
        ) not in (None, "pending", False)

        if reg_is_pending and meta_is_final:
            entry["engine_installation"] = meta_install
        elif not reg_install:
            entry["engine_installation"] = meta_install
        elif meta_install.get("installed") and not reg_install.get("installed"):
            entry["engine_installation"] = meta_install

        return entry

    @staticmethod
    def _resolve_engine_installation(engine, version):
        """Return immediate install status when engine is already available."""
        engine_lower = (engine or "").lower().strip()
        version = (version or "").strip()
        if not engine_lower or not version:
            return None

        if engine_lower in ("python", "py"):
            installed, message = EngineInstaller.is_python_installed(version)
            if installed:
                return {
                    "status": True,
                    "message": message,
                    "engine": "python",
                    "version": version,
                    "installed": True,
                }
        elif engine_lower in ("nodejs", "node", "js"):
            installed, message = EngineInstaller.is_nodejs_installed(version)
            if installed:
                return {
                    "status": True,
                    "message": message,
                    "engine": "nodejs",
                    "version": version,
                    "installed": True,
                }

        return {
            "status": "pending",
            "message": "Engine installation running in background",
            "engine": engine_lower,
            "version": version,
            "installed": False,
        }

    @staticmethod
    def _run_engine_install_background(
        engine,
        version,
        registry_path,
        metadata_path,
        module_name,
    ):
        """Install engine without blocking the upload HTTP response."""
        try:
            engine_install_result = EngineInstaller.install_engine(engine, version)
            if not os.path.isfile(registry_path) or not os.path.isfile(metadata_path):
                return

            with open(registry_path, "r", encoding="utf-8") as rf:
                registry = json.load(rf)

            with open(metadata_path, "r", encoding="utf-8") as mf:
                metadata = json.load(mf)

            for entry in registry:
                if entry.get("intelligence_name") == module_name:
                    entry["engine_installation"] = engine_install_result
                    break

            metadata["engine_installation"] = engine_install_result

            with open(registry_path, "w", encoding="utf-8") as rf:
                json.dump(registry, rf, indent=2)

            with open(metadata_path, "w", encoding="utf-8") as mf:
                json.dump(metadata, mf, indent=2)

            if engine_install_result.get("installed"):
                print(
                    f"[SUCCESS] Background engine install for {module_name}: "
                    f"{engine_install_result.get('message')}"
                )
            else:
                print(
                    f"[WARNING] Background engine install for {module_name}: "
                    f"{engine_install_result.get('message')}"
                )
        except Exception as exc:
            print(f"[ERROR] Background engine install failed: {exc}")

    # ---------------------------------------------------
    # Validate uploaded code
    # ---------------------------------------------------

    @staticmethod
    def validate_code(code_content):

        dangerous_patterns = [

            r"import\s+subprocess",

            r"from\s+subprocess",

            r"eval\s*\(",

            r"exec\s*\(",

            r"os\.system",

            r"__import__"
        ]

        for pattern in dangerous_patterns:

            if re.search(pattern, code_content):

                return False, f"Dangerous code detected: {pattern}"

        try:

            compile(code_content, "<string>", "exec")

        except SyntaxError as e:

            return False, f"Syntax error: {e}"

        return True, "Valid code"

    # ---------------------------------------------------
    # Extract functions
    # ---------------------------------------------------

    @staticmethod
    def extract_functions(code_content):

        functions = []

        try:

            tree = ast.parse(code_content)

            for node in ast.walk(tree):

                if isinstance(node, ast.FunctionDef):

                    if not node.name.startswith("_"):

                        functions.append({

                            "name": node.name,

                            "description": ast.get_docstring(node)
                        })

        except Exception as e:

            print(f"[ERROR] Function extraction failed: {e}")

        return functions

    # ---------------------------------------------------
    # Get UUID from controller
    # ---------------------------------------------------

    @staticmethod
    def get_uuid_from_controller(intelligence_name, agent_name):
        response = requests.post(
        "http://controller:9000/generate-uuid",
        timeout=5
        )

        response.raise_for_status()

        return response.json()["uuid"]


    # ---------------------------------------------------
    # Create metadata
    # ---------------------------------------------------

    @staticmethod
    def create_metadata(filename, functions, lines, agent_name, description=None, existing_uuid=None, intelligence_name=None,):

        if existing_uuid:
            intelligence_uuid = existing_uuid
        else:
            intelligence_uuid = (
                IntelligenceUploadHandler.get_uuid_from_controller(
                    filename[:-3],
                    agent_name
                )
            )

        metadata = {

            "intelligence_id": intelligence_uuid,

            "intelligence_name": intelligence_name,

            "filename": filename,

            "module_name": filename[:-3],

            "description": description or "",

            "created_at": datetime.utcnow().isoformat(),

            "status": "active",

            "functions": functions,

            "data_file": (
                f"/app/agents/{agent_name}/intel_definitions/"
                f"{filename[:-3]}.data"
            ),

            "metadata_file": (
                f"/app/agents/{agent_name}/intel_definitions/"
                f"{filename[:-3]}_metadata.json"
            )
        }

        return metadata

    # ---------------------------------------------------
    # Save uploaded intelligence
    # ---------------------------------------------------

   
    @staticmethod
    def save_uploaded_file(
        filename,
        code_content,
        agent_name,
        intelligence_name=None,
        description=None,
        engine=None,
        version=None,
    ):

        # -----------------------------------------
        # Validate code
        # -----------------------------------------

        valid, message = (
            IntelligenceUploadHandler.validate_code(
                code_content
            )
        )

        if not valid:
            return False, message, None, None, None

        target_filename = secure_filename(filename)

        #region agent log
        try:
            _log_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))
                        )
                    )
                ),
                "debug-552a44.log",
            )
            with open(_log_path, "a", encoding="utf-8") as _lf:
                _lf.write(
                    json.dumps(
                        {
                            "sessionId": "552a44",
                            "location": "intelligence_upload_handler.py:save",
                            "message": "filename resolution",
                            "data": {
                                "uploadedFilename": filename,
                                "intelligenceName": intelligence_name,
                                "targetFilename": target_filename,
                            },
                            "timestamp": int(datetime.utcnow().timestamp() * 1000),
                            "hypothesisId": "B",
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        #endregion

        # -----------------------------------------
        # Validate filename
        # -----------------------------------------

        secure_name, error = (
            IntelligenceUploadHandler.validate_filename(
                target_filename,
                agent_name
            )
        )

        is_update = (error == "FILE_EXISTS")

        # -----------------------------------------
        # Extract functions
        # -----------------------------------------

        functions = (
            IntelligenceUploadHandler.extract_functions(
                code_content
            )
        )

        existing_uuid = None

        if is_update:
            existing = IntelligenceUploadHandler._load_existing_upload(
                secure_name,
                agent_name
            )

            if existing:
                old_metadata, _, _ = existing
                existing_uuid = old_metadata.get("intelligence_id")

        try:

            # -----------------------------------------
            # Save uploaded .py file
            # -----------------------------------------
            intel_path = f"/app/agents/{agent_name}/intel_definitions"
            agent_base_path = f"/app/agents/{agent_name}"
            os.makedirs(

                intel_path,

                exist_ok=True
            )

            file_path = os.path.join(

                intel_path,

                secure_name
            )

            with open(file_path, "w", encoding="utf-8") as f:

                f.write(code_content)

            # -----------------------------------------
            # Create metadata
            # -----------------------------------------
            
            existing_uuid = None

            metadata_path = os.path.join(
                intel_path,
                f"{secure_name[:-3]}_metadata.json"
            )

            if os.path.exists(metadata_path):

                with open(metadata_path, "r", encoding="utf-8") as mf:

                    old_metadata = json.load(mf)

                existing_uuid = old_metadata.get("intelligence_id")

            metadata = (
                IntelligenceUploadHandler.create_metadata(

                    secure_name,

                    functions,

                    len(code_content.split("\n")),

                    agent_name,

                    description,
                    existing_uuid,
                    intelligence_name
                )
            )

            metadata_path = os.path.join(

                intel_path,

                f"{secure_name[:-3]}_metadata.json"
            )

            with open(metadata_path, "w", encoding="utf-8") as mf:

                json.dump(metadata, mf, indent=2)

            # -----------------------------------------
            # Execute uploaded intelligence
            # -----------------------------------------

            if os.getcwd() not in sys.path:
                sys.path.insert(0, os.getcwd())

            module_name = (
                f"agents.{agent_name}.intel_definitions.{secure_name[:-3]}"
            )

            print("========== DEBUG IMPORT ==========")
            print("INTEL_PATH:", intel_path)
            print("MODULE_NAME:", module_name)
            print("CURRENT_DIR:", os.getcwd())
            print("SYS_PATH:", sys.path[:5])

            try:
                import traceback

                if module_name in sys.modules:
                                del sys.modules[module_name]

                importlib.invalidate_caches()

                captured_output = io.StringIO()

                with redirect_stdout(captured_output):
                    module = importlib.import_module(module_name)

                execution_result = {
                    "output": captured_output.getvalue()
                }

            except Exception:
                print("========== IMPORT FAILED ==========")
                traceback.print_exc()
                print("===================================")
                raise

            # -----------------------------------------
            # Sample data
            # -----------------------------------------

            sample_data = {

                "co2": random.randint(300, 900),

                "temperature": random.randint(20, 40),

                "humidity": random.randint(30, 90),

                "traffic": random.randint(10, 100),

                "noise": random.randint(40, 120)
            }

            execution_result = {
                "output": captured_output.getvalue()
            }

            # -----------------------------------------
            # Execute all discovered functions
            # -----------------------------------------

            # for func in functions:

            #     func_name = func["name"]

            #     if hasattr(module, func_name):

            #         callable_func = getattr(module, func_name)

            #         try:

            #             result = callable_func(sample_data)

            #         except TypeError:

            #             result = callable_func()

            #         execution_result[func_name] = result

            # -----------------------------------------
            # Store output in .data file
            # -----------------------------------------

            data_file_path = os.path.join(

                intel_path,

                f"{secure_name[:-3]}.data"
            )

            with open(data_file_path, "w", encoding="utf-8") as df:

                json.dump(execution_result, df, indent=2)

            # -----------------------------------------
            # Update created_intelligence.json
            # -----------------------------------------

            registry_path = os.path.join(
                agent_base_path,
                "created_intelligence.json",
            )

            if os.path.exists(registry_path):

                with open(
                    registry_path,
                    "r",
                    encoding="utf-8"
                ) as rf:

                    registry = json.load(rf)

            else:

                registry = []

            module_name = secure_name[:-3]
            rel_impl_path = (
                f"agents/{agent_name}/intel_definitions/{secure_name}"
            )
            rel_result_path = f"intel_definitions/{module_name}.data"

            file_extension = (
                secure_name.rsplit(".", 1)[1].lower()
                if "." in secure_name
                else "py"
            )

            registry_entry = {
                "uuid": metadata["intelligence_id"],
                "intelligence_name": intelligence_name or module_name,
                "description": description or "Uploaded intelligence",
                "implementation_path": rel_impl_path,
                "extension": file_extension,
                "engine": engine or "python",
                "version": version or "",
                "result_path": rel_result_path,
                "execution_data": execution_result,
                "result_data": execution_result,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",
            }

            registry = [
                entry
                for entry in registry
                if entry.get("uuid") != metadata["intelligence_id"]
            ]
            registry.append(registry_entry)

            with open(
                registry_path,
                "w",
                encoding="utf-8"
            ) as rf:

                json.dump(registry, rf, indent=2)

            metadata["implementation_path"] = rel_impl_path
            metadata["result_path"] = rel_result_path

            # -----------------------------------------
            # Install Engine if specified (non-blocking)
            # -----------------------------------------

            if engine and version:
                engine_install_status = (
                    IntelligenceUploadHandler._resolve_engine_installation(
                        engine, version
                    )
                )
                registry_entry["engine_installation"] = engine_install_status
                metadata["engine_installation"] = engine_install_status

                with open(registry_path, "w", encoding="utf-8") as rf:
                    json.dump(registry, rf, indent=2)

                with open(metadata_path, "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf, indent=2)

                if engine_install_status.get("status") == "pending":
                    print(
                        f"[INFO] Scheduling background engine install: "
                        f"{engine} {version}"
                    )
                    threading.Thread(
                        target=IntelligenceUploadHandler._run_engine_install_background,
                        args=(
                            engine,
                            version,
                            registry_path,
                            metadata_path,
                            module_name,
                        ),
                        daemon=True,
                    ).start()
                else:
                    print(
                        f"[INFO] Engine already available: "
                        f"{engine_install_status.get('message')}"
                    )

            print(
                f"[INFO] Intelligence uploaded and executed: "
                f"{secure_name}"
            )

            return (
                True,
                "Upload successful",
                metadata,
                registry_entry,
                execution_result,
            )

        except Exception as e:
            import traceback

            print("\n===== FULL TRACEBACK =====")
            traceback.print_exc()
            print("==========================\n")

            return False, str(e), None, None, None

    # ---------------------------------------------------
    # Upload instructions
    # ---------------------------------------------------

    @staticmethod
    def get_upload_instructions():

        return {

            "title": "Upload Intelligence",

            "requirements": [

                "Python (.py) files only",

                "At least one function required",

                "No dangerous imports",

                "Maximum file size 100KB"
            ],

            "example": '''

def pollution_alert(data):

    co2 = data["co2"]

    if co2 > 700:

        return {
            "status": "HIGH",
            "co2": co2
        }

    return {
        "status": "NORMAL",
        "co2": co2
    }

''',

            "workflow": [

                "Upload .py file",

                "Controller generates UUID",

                "Intelligence executes automatically",

                "Output stored in filename.data",

                "Repository displays result"
            ]
        }

