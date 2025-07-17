# dashboard.dockerfile

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY ./central_app/ /app/

# Install Python dependencies
RUN pip install flask requests

# Create required directory 
RUN mkdir -p /app/data/received

# Expose Flask port
EXPOSE 8000

# Run the Flask app
CMD ["python", "app.py"]
