FROM node:22-alpine AS web

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM pgvector/pgvector:pg16

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    FORGE_PLANNER=keyword \
    FORGE_API_KEY=dev-api-key \
    FORGE_DATABASE_URL=postgresql://forge@127.0.0.1:5432/forge \
    FORGE_CORPUS_DIR=/app/corpus \
    FORGE_SANDBOX_ROOT=/tmp/forge-sandbox \
    FORGE_TOOL_TRANSPORT=inprocess \
    FASTEMBED_CACHE_PATH=/opt/fastembed \
    PGDATA=/var/lib/forge-pg

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip python3-venv nginx ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default

RUN python3 -m venv /opt/forge

WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/mcp_servers ./mcp_servers
COPY backend/corpus ./corpus
COPY backend/evals ./evals

RUN /opt/forge/bin/pip install --no-cache-dir . \
 && /opt/forge/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

COPY --from=web /src/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/forge.conf
COPY deploy/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80
ENTRYPOINT ["/start.sh"]
