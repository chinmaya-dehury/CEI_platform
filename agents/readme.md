# Agent1 - Traffic Monitoring AI Agent
##  Objectives
- Simulate traffic congestion levels.
- Periodically generate synthetic traffic data.
- Register itself with Consul for service discovery.
- Register with the central controller via `/register`.
- Make traffic data accessible via endpoints for monitoring.

##  Capabilities
- `GET /data` – Displays current traffic congestion value (low/medium/high) based on vehicle count
- `GET /history` – Displays traffic congestion history (last 5 minutes).
- `GET /capabilities` – Displays min/avg/max traffic values in last 5 minutes.
- Self-registers with Consul and Controller using its UUID and metadata.
- Logs data persistently in a Docker volume.
- Health-checked via Consul for system observability.

#  Agent2 – Air Quality Agent

### Objectives
- Generate synthetic CO2 data.
- Help evaluate environmental pollution.
- Register itself with Consul for service discovery.
- Register with the central controller via `/register`.
- Send data to the controller and Consul.

### Capabilities
- `/data` – Current CO2 level.
- `/history` – Last 5-minute data log.
- `/capabilities` – Min/Avg/Max CO2.
- Self-registers with Consul and Controller using its UUID and metadata.
- Logs data persistently in a Docker volume.
- Health-checked via Consul for system observability.

---


# 🔊 Agent3 – Noise Monitoring Agent

### Objectives
- Simulate real-time ambient noise levels.
- Generate synthetic noise level readings in decibels (dB).
- Register with the Consul service and central controller.
- Log data for short-term historical analysis.

### Capabilities
- `GET /data` – Displays current noise level (in dB).
- `GET /history` – Last 5 minutes of noise level data.
- `GET /capabilities` – Displays min/avg/max noise levels over 5 minutes.
- Periodic noise data generation every 30 seconds.
- Self-registers with controller and Consul at startup.
- Persists logs using Docker volume for observability.


#  Agent4 – Humidity Monitoring Agent

### Objectives
- Simulate live humidity sensor data.
- Provide environmental humidity metrics for observability.
- Log humidity levels and expose them to the controller.
- Integrate seamlessly with the service mesh (Consul).

### Capabilities
- `GET /data` – Displays current humidity level (in %).
- `GET /history` – Humidity data history for the last 5 minutes.
- `GET /capabilities` – Min/Avg/Max humidity levels computed over 5 minutes.
- Registers automatically with central controller and Consul.
- Periodically generates humidity readings every 30 seconds.
- Persistent data logging via Docker volume.

---

#  Agent5 – Temperature Monitoring Agent

### Objectives
- Generate and monitor synthetic temperature data.
- Report environmental temperature to the controller.
- Ensure consistent registration with Consul for service discovery.
- Maintain historical data for short-term analysis.

### Capabilities
- `GET /data` – Displays current temperature (in °C).
- `GET /history` – Displays temperature history for the last 5 minutes.
- `GET /capabilities` – Displays min/avg/max temperature in the last 5 minutes.
- Periodic data generation every 30 seconds.
- Auto-registers with controller and Consul.
- Logs temperature data using Docker volume.

---