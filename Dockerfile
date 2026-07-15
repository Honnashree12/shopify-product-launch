# Use official Python 3.11 slim image for resource efficiency
FROM python:3.11-slim

# Prevent Python from writing .pyc files and force unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install required system packages for networking and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project source directories and files
COPY agents/ ./agents/
COPY shopify_mock/ ./shopify_mock/
COPY tools/ ./tools/
COPY workflow/ ./workflow/
COPY data/ ./data/
COPY outputs/ ./outputs/
COPY static/ ./static/
COPY main.py .
COPY state.py .
COPY shopify_client.py .
COPY product_workflow.py .

# Expose target application port (Cloud Run defaults to 8080)
EXPOSE 8080

# Run FastAPI app via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
