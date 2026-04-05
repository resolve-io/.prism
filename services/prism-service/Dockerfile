FROM python:3.12-slim

WORKDIR /app

# Install system deps for SQLite FTS5
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Create data directory
RUN mkdir -p /data/mulch /data/workflow

EXPOSE 8080 8081

CMD ["python", "-m", "app.main"]
