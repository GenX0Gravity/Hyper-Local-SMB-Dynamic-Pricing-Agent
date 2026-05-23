FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for compiling psycopg2 and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/backend

# Set Python path to find the backend package
ENV PYTHONPATH=/app

# Expose port 8000
EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
