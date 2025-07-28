FROM python:3.9-slim

WORKDIR /app

# Copy necessary files

COPY search_service/search.py /app/search.py

# Install required Python packages
RUN pip install flask requests python-dateutil



EXPOSE 5006

CMD ["python", "search.py"]
