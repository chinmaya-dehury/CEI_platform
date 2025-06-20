FROM python:3.9
WORKDIR /app
COPY controller.py .
RUN pip install flask

COPY server/controller.py ./server/controller.py
CMD ["python", "server/controller.py"]


