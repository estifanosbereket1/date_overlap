FROM python:3.12-slim

# Install system dependencies needed by OpenCV and psycopg2
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
# COPY main.py bot.py cleardb.py .env ./
COPY main.py bot.py cleardb.py ./

# Default command (overridden per service in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]