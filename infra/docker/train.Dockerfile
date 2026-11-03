FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9.4 \
    /uv /uvx /bin/

# Dependencies and project metadata
COPY pyproject.toml uv.lock README.md ./

# Application source
COPY src/ ./src/

# Install Python dependencies and project
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# DVC metadata
COPY .dvc/ ./.dvc/
COPY data/ ./data/

RUN dvc config core.no_scm true --local

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "taxi_trip_duration.training_pipeline"]
