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


FEATURE_SETS = {
    "v1": [
        "PULocationID",
        "DOLocationID",
        "route_id",
        "pickup_borough",
        "dropoff_borough",
        "request_hour",
        "day_of_week",
        "is_weekend",
        "same_zone",
        "hvfhs_license_num",
        "shared_request_flag",
        "wav_request_flag",
    ],
}

FEATURE_SET_VERSION = "v1"

TARGET_COLUMN = "target_duration_sec"
