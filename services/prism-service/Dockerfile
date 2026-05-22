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

# System deps:
#   * gcc          — SQLite FTS5 build
#   * git          — source_service.ensure_cloned (v5.1+)
#   * curl, ca-certificates — node setup script needs them
#   * node + npm   — required by `@anthropic-ai/claude-code` (the `claude`
#                    CLI is a Node app), which the v5.1.6 understand_drainer
#                    invokes per-job. NodeSource provides a slim Node 22 LTS
#                    on Debian bookworm that won't drag in extra runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc git curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g --no-audit --no-fund @anthropic-ai/claude-code \
    && apt-get remove -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Sanity-check the claude binary landed on PATH so a broken image fails
# at build time, not when the drainer first tries to run.
RUN claude --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
# SPA bundle from the web-build stage (above) lands at app/web_dist/.
COPY --from=web-build /web_dist /app/app/web_dist

RUN mkdir -p /data/mulch /data/workflow

EXPOSE 7777 7778

CMD ["python", "-m", "app.main"]
