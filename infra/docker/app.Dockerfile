
# syntax=docker/dockerfile:1

# -------------------------------------------
# Stage 1: Install Python dependencies
# -------------------------------------------
FROM python:3.12-slim AS builder

# Use a pinned uv version for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

WORKDIR /app

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency definitions first for Docker layer caching.
COPY pyproject.toml uv.lock ./

# Install only production dependencies.
# The application source is copied into the runtime image.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project


# -------------------------------------------
# Stage 2: Runtime
# -------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    MODEL_URI="/app/models"

# Copy installed dependencies from builder.
COPY --from=builder /app/.venv /app/.venv

# Copy only the code and artifacts needed for inference.
COPY src/taxi_trip_duration /app/src/taxi_trip_duration
COPY models/ /app/models/

# Preserve the lookup path expected by config.py.
COPY data/raw/taxi_zone_lookup.csv /app/data/raw/taxi_zone_lookup.csv

# Run the application as a non-root user.
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --home-dir /app appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Basic container health check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "taxi_trip_duration.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
