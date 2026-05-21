FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app


COPY agents/temperature_agent ./agents/temperature_agent

RUN pip install flask requests

CMD ["python", "-m", "agents.temperature_agent.temperature_agent"]
