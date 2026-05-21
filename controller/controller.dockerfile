# Dockerfiles/controller.dockerfile
FROM python:3.9-slim

WORKDIR /app

<<<<<<< HEAD
COPY controller/ /app/
=======
COPY controller/controller.py /app/controller.py
>>>>>>> origin/main

RUN pip install --no-cache-dir flask requests

CMD ["python", "controller.py"]
