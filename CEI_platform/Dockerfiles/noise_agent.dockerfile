# Use Python base imageFROM python:3.9-slim
FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY data/ ./data/
COPY agents/ ./agents/

RUN pip install flask requests

CMD ["python", "-m", "agents.noise_agent.noise_agent"]