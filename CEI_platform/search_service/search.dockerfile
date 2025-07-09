FROM python:3.9-slim

WORKDIR /app

COPY ../data /app/data
COPY search_service/search.py /app/search.py
RUN pip install flask

EXPOSE 5006

CMD ["python", "search.py"]
