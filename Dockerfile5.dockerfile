FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY Agents/agent5.py ./agent5.py

CMD ["python", "agent5.py"]