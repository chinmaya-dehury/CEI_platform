# Use Python base image
FROM python:3.9-slim

WORKDIR /app
ENV PYTHONPATH=/app


COPY data/ ./data/
COPY agents/ ./agents/

RUN pip install flask requests

CMD ["python", "./agents/co2_agent.py"]

