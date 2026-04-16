# Per4Biz FastAPI — Fly.io Madrid deployment
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

# uv — fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.6 /uv /uvx /bin/

WORKDIR /app

# Install deps first (layer cache)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy app
COPY app ./app

# Install the project itself
RUN uv sync --frozen --no-dev

# -----------------------------------------------------

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash per4biz

WORKDIR /app

COPY --from=builder --chown=per4biz:per4biz /app /app

USER per4biz

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
