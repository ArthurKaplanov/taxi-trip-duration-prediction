.PHONY: dvc-add data data-sample lint train train-sample mlflow-local start-app-local test build-app run-app

PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff
DVC ?= .venv/bin/dvc
SAMPLE_ROWS ?= 1000000
PROCESSED_PATH ?= data/processed/fhvhv_tripdata_2026-05.parquet
TRAIN_REPORT_PATH ?= data/reports/training_metrics.json

test:
	uv run pytest

lint:
	uv run pre-commit run --all-files

dvc-add:
	$(DVC) add $(file)

mlflow-local:
	uv run mlflow server \
	--backend-store-uri sqlite:///mlflow.db \
	--default-artifact-root ./mlruns \
	--host 127.0.0.1 \
	--port 5005

mlflow-docker:
	docker-compose -f infra/docker/mlflow-docker-compose.yaml up -d

start-app-local:
	uv run uvicorn taxi_trip_duration.app:app --host 127.0.0.1 --port 8000 --reload

data:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline

data-sample:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline --sample-rows $(SAMPLE_ROWS) --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet --report-path data/reports/data_quality_2026-05_sample.json

train:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.training_pipeline --processed-path $(PROCESSED_PATH) --report-path $(TRAIN_REPORT_PATH)

train-sample:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.training_pipeline --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet --report-path data/reports/training_metrics_sample.json

build-app:
	docker build \
	-f infra/docker/app.Dockerfile \
	-t taxi-prediction:local-v3 \
	.
run-app:
	docker run --rm \
	--name taxi-prediction \
	-p 8000:8000 \
	taxi-prediction:local-v4
