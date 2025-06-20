FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY Agents/agent4.py ./agent4.py

CMD ["python", "agent4.py"]