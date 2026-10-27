from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_NAME = "fhvhv_tripdata_2026-05"

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / f"{DATASET_NAME}.parquet"
ZONE_LOOKUP_PATH = PROJECT_ROOT / "data" / "raw" / "taxi_zone_lookup.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / f"{DATASET_NAME}.parquet"
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "data_quality_2026-05.json"

REQUIRED_COLUMNS = [
    "PULocationID",
    "DOLocationID",
    "request_datetime",
    "pickup_datetime",
    "dropoff_datetime",
    "hvfhs_license_num",
    "shared_request_flag",
    "wav_request_flag",
]

MODEL_INPUT_COLUMNS = [
    "PULocationID",
    "DOLocationID",
    "request_datetime",
    "hvfhs_license_num",
    "shared_request_flag",
    "wav_request_flag",
]

DATETIME_COLUMNS = [
    "request_datetime",
    "pickup_datetime",
    "dropoff_datetime",
]
