# Gmail Calendar Sync - Multi-stage Docker Build

# Stage 1: builder - installs only production deps into .venv
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-cache --no-dev


# Stage 2: test - adds dev deps and test code on top of builder
FROM builder AS test

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN uv sync --frozen --no-cache --all-extras --all-groups
COPY src/ ./src/
COPY tests/ ./tests/

CMD ["python", "-m", "pytest", "tests/", "-v"]


# Stage 3: production - only the venv and source, nothing else
FROM python:3.13-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
RUN chown -R appuser:appuser /app

USER appuser
CMD ["python", "-m", "src.main"]
