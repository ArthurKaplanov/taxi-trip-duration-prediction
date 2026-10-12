.PHONY: dvc-add data data-sample lint

PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff
DVC ?= .venv/bin/dvc
SAMPLE_ROWS ?= 1000000

lint:
	uv run pre-commit run --all-files

dvc-add:
	$(DVC) add $(file)

data:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline

data-sample:
	PYTHONPATH=src $(PYTHON) -m taxi_trip_duration.data_pipeline --sample-rows $(SAMPLE_ROWS) --processed-path data/processed/fhvhv_tripdata_2026-05_sample.parquet --report-path data/reports/data_quality_2026-05_sample.json
