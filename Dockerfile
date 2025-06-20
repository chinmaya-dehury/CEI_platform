
# Use Python base image
# Use Python base image
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY Agents/agent1.py ./agent1.py

CMD ["python", "agent1.py"]
