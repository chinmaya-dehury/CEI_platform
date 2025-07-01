# dashboard.dockerfile

FROM python:3.9-slim

WORKDIR /app

COPY ./central_app/ /app/


RUN pip install flask requests

EXPOSE 8000

CMD ["python", "app.py"]
