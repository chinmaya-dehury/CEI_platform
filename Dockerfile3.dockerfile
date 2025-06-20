# Use Python base image
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY Agents/agent3.py .
CMD ["python", "agent3.py"]

