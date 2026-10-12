import argparse
import json
from pathlib import Path

import fastparquet
import pandas as pd

from taxi_trip_duration.config import (
    DATASET_NAME,
    MODEL_INPUT_COLUMNS,
    PROCESSED_DATA_PATH,
    RAW_DATA_PATH,
    REPORT_PATH,
    REQUIRED_COLUMNS,
)
from taxi_trip_duration.preprocessing import preprocess_trips
from taxi_trip_duration.validation import (
    build_invalid_mask,
    build_quality_report,
    require_columns,
)


def read_raw_data(raw_data_path: Path, sample_rows: int | None = None) -> pd.DataFrame:
    if sample_rows is None:
        return pd.read_parquet(raw_data_path)
    if sample_rows <= 0:
        raise ValueError("sample_rows must be a positive integer")

    return fastparquet.ParquetFile(raw_data_path).head(sample_rows)


def run_data_pipeline(
    raw_data_path: Path = RAW_DATA_PATH,
    processed_data_path: Path = PROCESSED_DATA_PATH,
    report_path: Path = REPORT_PATH,
    sample_rows: int | None = None,
) -> dict:
    df_raw = read_raw_data(raw_data_path, sample_rows)
    require_columns(df_raw, REQUIRED_COLUMNS)

    invalid_mask = build_invalid_mask(df_raw, REQUIRED_COLUMNS)
    df_processed = preprocess_trips(df_raw, MODEL_INPUT_COLUMNS, invalid_mask)

    report = build_quality_report(
        df_raw=df_raw,
        df_processed=df_processed,
        dataset_name=DATASET_NAME,
        required_columns=REQUIRED_COLUMNS,
        invalid_mask=invalid_mask,
    )

    processed_data_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df_processed.to_parquet(processed_data_path, index=False)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-path", type=Path, default=RAW_DATA_PATH)
    parser.add_argument("--processed-path", type=Path, default=PROCESSED_DATA_PATH)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--sample-rows", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = run_data_pipeline(
        raw_data_path=args.raw_path,
        processed_data_path=args.processed_path,
        report_path=args.report_path,
        sample_rows=args.sample_rows,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
