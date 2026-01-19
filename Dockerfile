# Use official Python lightweight image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 80 (Standard for CapRover)
EXPOSE 80

# Set environment variable for port
ENV PORT=80

# Command to run the application using Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:80", "server:app"]
