.PHONY: dvc-add data data-sample lint train train-sample

PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff
DVC ?= .venv/bin/dvc
SAMPLE_ROWS ?= 1000000
PROCESSED_PATH ?= data/processed/fhvhv_tripdata_2026-05.parquet
TRAIN_REPORT_PATH ?= data/reports/training_metrics.json

lint:
	uv run pre-commit run --all-files

dvc-add:
	$(DVC) add $(file)

data:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline

data-sample:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline --sample-rows $(SAMPLE_ROWS) --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet --report-path data/reports/data_quality_2026-05_sample.json

train:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.training_pipeline --processed-path $(PROCESSED_PATH) --report-path $(TRAIN_REPORT_PATH)

train-sample:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.training_pipeline --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet --report-path data/reports/training_metrics_sample.json
