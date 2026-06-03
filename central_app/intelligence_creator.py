import re
import requests
from werkzeug.utils import secure_filename
import os


DEFAULT_AGENT_PORTS = {
    "traffic_agent": 5000,
    "co2_agent": 5001,
    "noise_agent": 5002,
    "humidity_agent": 5003,
    "temperature_agent": 5004,
}


def is_running_in_docker():
    """Best-effort detection for Docker Compose service-to-service URLs."""
    return os.path.exists("/.dockerenv")


def module_filename_from_intelligence_name(intelligence_name):
    """Derive a safe .py filename from the form intelligence name."""
    base = secure_filename(intelligence_name.strip().lower().replace(" ", "_"))
    if not base:
        return None
    if not re.match(r"^[a-z]", base):
        base = f"i_{base}"
    if not base.endswith(".py"):
        base = f"{base}.py"
    return base


def resolve_agent_url(agent_name, port=5001):
    """
    Resolve the URL for an agent.
    Tries multiple approaches:
    1. Check for environment variable override (CO2_AGENT_URL, etc.)
    2. Check AGENT_HOST environment variable
    3. Try localhost (for local development)
    
    Args:
        agent_name: Name of the agent
        port: Port number (default 5001)
        
    Returns:
        Base URL for the agent
        
    Environment Variables:
        - {AGENT_NAME_UPPER}_URL: Full URL override (e.g., CO2_AGENT_URL)
        - {AGENT_NAME_UPPER}_HOST: Host override (e.g., CO2_AGENT_HOST)
        - {AGENT_NAME_UPPER}_PORT: Port override (e.g., CO2_AGENT_PORT)
        - AGENT_HOST: Default host for all agents (default: localhost)
        - AGENT_PORT: Default port for all agents (default: 5001)
    """
    # Check for full URL override
    env_key = f"{agent_name.upper()}_URL"
    if env_key in os.environ:
        return os.environ[env_key]
    
    # Check for host override
    env_host_key = f"{agent_name.upper()}_HOST"
    if env_host_key in os.environ:
        agent_host = os.environ[env_host_key]
    else:
        # In Docker Compose, service names resolve on the app network.
        default_host = agent_name if is_running_in_docker() else "localhost"
        agent_host = os.environ.get("AGENT_HOST", default_host)
    
    # Check for port override
    env_port_key = f"{agent_name.upper()}_PORT"
    if env_port_key in os.environ:
        try:
            port = int(os.environ[env_port_key])
        except ValueError:
            pass
    else:
        # Use global default port if set
        if "AGENT_PORT" in os.environ:
            try:
                port = int(os.environ["AGENT_PORT"])
            except ValueError:
                pass
    
    return f"http://{agent_host}:{port}"


def forward_intelligence_to_agent(
    agent_name,
    intelligence_name,
    description,
    file,
    engine=None,
    version=None,
    port=None,
):
    """Forward intelligence file to an agent for processing.
    
    Args:
        agent_name: Name of the agent
        intelligence_name: Name of the intelligence
        description: Description of the intelligence
        file: File object to upload
        engine: Runtime engine (optional, e.g., 'python', 'nodejs')
        version: Engine version (optional)
        port: Agent port (optional, uses defaults if not provided)
    """

    try:
        # Use provided port or resolve from defaults. Keep this local to avoid
        # importing app.py from inside a request handler.
        if port is None:
            port = DEFAULT_AGENT_PORTS.get(agent_name, 5001)

        base_url = resolve_agent_url(agent_name, port=port)
        upload_url = f"{base_url}/upload-intelligence"

        module_filename = module_filename_from_intelligence_name(intelligence_name)
        if not module_filename:
            return {
                "status": "error",
                "message": "Invalid intelligence name",
            }

        file.stream.seek(0)
        files = {
            "file": (
                module_filename,
                file.stream,
                "text/x-python"
            )
        }

        data = {
            "intelligence_name": intelligence_name,
            "description": description,
            "engine": engine or "",
            "version": version or "",
        }

        response = requests.post(
            upload_url,
            files=files,
            data=data,
            timeout=120,
        )

        if response.status_code not in [200, 201]:
            message = response.text
            try:
                error_body = response.json()
                message = (
                    error_body.get("message")
                    or error_body.get("error")
                    or message
                )
            except ValueError:
                pass

            return {
                "status": "error",
                "message": message,
                "http_status": response.status_code,
            }

        response_data = response.json()

        return {

            "status": "success",

            "agent_name": agent_name,

            "intelligence_name": intelligence_name,

            "response": response_data
        }

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to agent {agent_name}. Error: {str(e)}\n\n"
        error_msg += f"Attempted URL: {resolve_agent_url(agent_name)}/upload-intelligence\n\n"
        error_msg += "TROUBLESHOOTING:\n"
        error_msg += "1. Ensure the agent is running\n"
        error_msg += "2. Verify the agent address is correct\n"
        error_msg += "3. For local development, set environment variables:\n"
        error_msg += f"   - {agent_name.upper()}_HOST=localhost (or your machine IP)\n"
        error_msg += f"   - {agent_name.upper()}_PORT=5001 (or your agent port)\n"
        error_msg += "4. Or set a full URL override:\n"
        error_msg += f"   - {agent_name.upper()}_URL=http://localhost:5001"
        
        return {
            "status": "error",
            "message": error_msg
        }
    
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": f"Request to agent {agent_name} timed out after 120 seconds. The agent may be slow or unresponsive."
        }
    
    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
