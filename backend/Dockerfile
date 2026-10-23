FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN useradd --create-home --uid 10001 forge

COPY pyproject.toml ./
COPY app ./app
COPY mcp_servers ./mcp_servers
COPY corpus ./corpus
COPY evals ./evals

RUN pip install --no-cache-dir .

USER forge

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
