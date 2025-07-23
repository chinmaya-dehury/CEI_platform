# CEI_platform
Platform for Clustered Edge Intelligence with discoverability and obserability capabilities.

## Overall Sy.
![Overall Sy](./doc/system_architecture.pdf)

### Registration process
![registration process](./doc/agentstraffic.drawio.pdf)

Intelligent Agent System with Web Dashboard:-

*OVERALL SYSTEM:-
This system is a distributed microservice-based infrastructure built for smart city applications. It integrates several AI-powered sensor agents that monitor environmental and traffic conditions. These agents are registered with a Consul service mesh for health tracking and service discovery. A central Flask-based web application serves as the control and monitoring interface

**SYSTEM ARCHITECTURE:-
![Sys arch](./doc/total_sys_arch.drawio.pdf)


   Web Application
1) Introduction:-
   
     -The central WebApp is built using Flask and provides:
   
     -Acts as the main control and monitoring interface for all agents.
   
     -Uses Consul for automatic service discovery and health tracking.

     -Offers RESTful API endpoints like:

     -/intelligence, /health, /search, /data/export/json, etc.

     -Supports data export in JSON/CSV format for offline use.

    -Easily scalable — new agents auto-register and appear in the dashboard.
   

3) Dashboard for all active agents:-

    -Access to intelligence data (e.g., CO2, humidity, noise) at localhost:8000/intelligence
   
    -Shows a table of all active agents with their health status whether reachable or not

 Features

(i) Auto-discovery of agents via Consul

(ii) Data aggregation and analysis endpoints

(iii) JSON/CSV export of intelligence logs

(iv) Health status of all agents available if active shows reachable and if not unreachable 

(v) Shows agents port addresses and locations

***Installation & Configuration

 Environment

 (i) OS: Windows

(ii) Docker & Docker Compose

(iii) Python 3.10+

IDEs

(i) Visual Studio Code

LIBRARIES:-
(i) flask
(ii) requests
(iii) python-dateutil
 
PRE-REQUISITES:-

Installation of docker.io and docker-compose

        sudo apt install docker.io docker-compose
            
Installation of python 3 and python3-pip

       sudo apt install python3 python3-pip
       

 Installation of consul

        wget https://releases.hashicorp.com/consul/1.15.4/consul_1.15.4_linux_amd64.zip

         unzip consul_1.15.4_linux_amd64.zip

        sudo mv consul /usr/local/bin/


INSTALLATION STEPS:-
(i) git clone: https://github.com/chinmaya-dehury/CEI_platform.git

(ii) cd "CEI_platform_fresh"

(iii) docker-compose up --build(to build the containers)

(iv) docker-compose up(if already built)

How to Use

(i) It starts Consul and all agent containers

(ii) Start the Central_app(web app) (app.py)

For example to discover the health status via an endpoint


     http://localhost:5000/health  (traffic_agent)
     http://localhost:5001/health  (co2_agent)
     http://localhost:5002/health  (noise_agent)
     http://localhost:5003/health  (humidity_agent)
     http://localhost:5004/health  (temperature_agent)
     http://localhost:5006/search?requirement=co2_agent  (search_app - an example search for one of the agents)
     
Explore endpoints like:

| Endpoint                    | Method | Description                                                                            | Output Format |
| --------------------------- | ------ | -------------------------------------------------------------------------------------- | ------------- |
| `/data`                     | GET    | Displays the latest **raw sensor data** from the agent.                                 | JSON          |
| `/description`              | GET    | Displays **agent metadata**, including name, UUID, unit, frequency, and location.       | JSON          |
| `/intelligence`             | GET    | Displays **analyzed data** (average, min, max) over recent timeframe (e.g., 5 minutes). | JSON          |
| `/download-uuid`            | GET    | Provides the agent’s **unique UUID** (identifier).                                     | JSON / Plain  |
| `/health`                   | GET    | Shows agent's **health status** (`Healthy`, `Unreachable`, etc.).                      | JSON          |
| `/data/export/json`         | GET    | Exports the **full raw data log** in **JSON** format.                                  | JSON file     |
| `/data/export/csv`          | GET    | Exports the **full raw data log** in **CSV** format.                                   | CSV file      |
| `/intelligence/export/json` | GET    | Exports **intelligence records** (aggregated data) in **JSON** format.                 | JSON file     |


Testing & Access

Consul UI: http://localhost:8500 (for service discoverability)

WebApp UI: http://localhost:8000  (for dashboard central_app) and http://localhost:8000/intelligence (central_app intelligence list)



## Agents Overview

| Agent Name        | Intelligence Type   | Endpoint Example          | Info                     |
|-------------------|---------------------|----------------------------|--------------------------|
| `traffic_agent`   | Traffic congestion  | `/data`, `/intelligence`  | Vehicle counts in %      |
| `co2_agent`       | CO₂ emissions        | `/data`, `/intelligence`  | CO₂ levels in ppm        |
| `humidityagent`   | Humidity sensing    | `/data`, `/intelligence`  | Humidity %               |
| `temperatureagent`| Temperature         | `/data`, `/intelligence`  | Temperature in °C        |
| `noiseagent`      | Noise pollution     | `/data`, `/intelligence`  | Noise in dB              |

Agent Registration (Consul + System)

 Auto-Registration Sample

    def register_with_consul(): 
    service = {
        "ID": metadata["uuid"],
        "Name": AGENT_NAME,
        "Address": AGENT_NAME,
        "Port": PORT,
        "Meta": {"type": "sensor", "location": "sector-5"},
        "Check": {
            "HTTP": f"http://{AGENT_NAME}:{PORT}/health",
            "Interval": "10s"
        }
    }
    requests.put(f"http://consul:8500/v1/agent/service/register", json=service)

component access:-

Consul UI: http://localhost:8500

WebApp: http://localhost:5006

Agents: Registered and accessed via Docker hostnames (e.g., http://localhost:5000/health)





















