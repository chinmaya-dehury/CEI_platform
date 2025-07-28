FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app


COPY agents/humidity_agent ./agents/humidity_agent

RUN pip install flask requests

CMD ["python", "-m", "agents.humidity_agent.humidity_agent"]

