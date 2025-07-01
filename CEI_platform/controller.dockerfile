FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install flask requests

CMD ["python", "controller.py"]
#gbgbfvfvr#
