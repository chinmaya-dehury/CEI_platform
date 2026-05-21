# Dockerfiles/controller.dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY controller/ /app/

RUN pip install --no-cache-dir flask requests

CMD ["python", "controller.py"]
