# ---- SPA build ----------------------------------------------------------
FROM node:22-slim AS web-build
WORKDIR /web
COPY app/web/package.json app/web/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY app/web/ ./
RUN npm run build

# ---- Service ------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# System deps: gcc (SQLite FTS5 build), git (v5.1 source_service.ensure_cloned).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
# SPA bundle from the web-build stage (above) lands at app/web_dist/.
COPY --from=web-build /web_dist /app/app/web_dist

RUN mkdir -p /data/mulch /data/workflow

EXPOSE 7777 7778

CMD ["python", "-m", "app.main"]
