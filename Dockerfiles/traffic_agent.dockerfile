FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app


COPY agents/traffic_agent ./agents/traffic_agent

RUN pip install flask requests

CMD ["python", "-m", "agents.traffic_agent.traffic_agent"]

