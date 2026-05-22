import os
import uuid
import importlib

from flask import Flask, jsonify


app = Flask(__name__)


INTELLIGENCE_FOLDER = "agents.co2_agent.intel_definitions"

FOLDER_PATH = "agents/co2_agent/intel_definitions"


intelligence_registry = []


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

    return jsonify({

        "agent_name": "co2_agent",

        "intelligence": intelligence_registry

    })


@app.route("/")
def home():

    return jsonify({
        "message": "CO2 Intelligence Service Running"
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5010)