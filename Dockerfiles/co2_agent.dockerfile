# Use Python base image
FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app


COPY agents/ ./agents/

RUN pip install flask requests

CMD ["python", "-m", "agents.co2_agent.co2_agent"]

