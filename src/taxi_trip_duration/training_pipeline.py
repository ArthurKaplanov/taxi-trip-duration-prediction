"""Simple training pipeline for the taxi trip duration model."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from taxi_trip_duration.config import (
    FEATURE_SET_VERSION,
    FEATURE_SETS,
    PROCESSED_DATA_PATH,
    PROJECT_ROOT,
    TARGET_COLUMN,
)
from taxi_trip_duration.features_engineering import build_features
from taxi_trip_duration.train import (
    calculate_metrics,
    time_split,
    train_catboost_regressor,
    train_dummy_regression,
)

CATEGORICAL_FEATURES = [
    "PULocationID",
    "DOLocationID",
    "route_id",
    "pickup_borough",
    "dropoff_borough",
    "hvfhs_license_num",
    "shared_request_flag",
    "wav_request_flag",
]

TRAINING_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "training_metrics.json"


def prepare_model_input(
    df: pd.DataFrame,
    feature_columns: list[str],
    cat_features: list[str],
) -> pd.DataFrame:
    X = df[feature_columns].copy()

    for column in cat_features:
        if column in X.columns:
            X[column] = X[column].astype(str)

    return X


def run_training_pipeline(
    processed_data_path: Path = PROCESSED_DATA_PATH,
    report_path: Path = TRAINING_REPORT_PATH,
    feature_set_version: str = FEATURE_SET_VERSION,
) -> dict:
    df = pd.read_parquet(processed_data_path)
    df = build_features(df)

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")
    if feature_set_version not in FEATURE_SETS:
        raise ValueError(f"Unknown feature set version: {feature_set_version}")

    feature_columns = FEATURE_SETS[feature_set_version]
    cat_features = [
        column for column in CATEGORICAL_FEATURES if column in feature_columns
    ]

    train_df, val_df, test_df = time_split(df)

    X_train = prepare_model_input(train_df, feature_columns, cat_features)
    X_val = prepare_model_input(val_df, feature_columns, cat_features)
    X_test = prepare_model_input(test_df, feature_columns, cat_features)

    y_train = train_df[TARGET_COLUMN]
    y_val = val_df[TARGET_COLUMN]
    y_test = test_df[TARGET_COLUMN]

    dummy_model = train_dummy_regression(y_train)
    dummy_val_pred = dummy_model.predict(np.zeros((len(y_val), 1)))
    dummy_test_pred = dummy_model.predict(np.zeros((len(y_test), 1)))

    catboost_model = train_catboost_regressor(
        X_train,
        y_train,
        cat_features=cat_features,
        X_val=X_val,
        y_val=y_val,
    )
    catboost_val_pred = catboost_model.predict(X_val)
    catboost_test_pred = catboost_model.predict(X_test)

    report = {
        "feature_set_version": feature_set_version,
        "rows": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
        "features": feature_columns,
        "cat_features": cat_features,
        "metrics": {
            "dummy": {
                "val": calculate_metrics(y_val, dummy_val_pred),
                "test": calculate_metrics(y_test, dummy_test_pred),
            },
            "catboost": {
                "val": calculate_metrics(y_val, catboost_val_pred),
                "test": calculate_metrics(y_test, catboost_test_pred),
            },
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-path", type=Path, default=PROCESSED_DATA_PATH)
    parser.add_argument("--report-path", type=Path, default=TRAINING_REPORT_PATH)
    parser.add_argument("--feature-set-version", default=FEATURE_SET_VERSION)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    training_report = run_training_pipeline(
        processed_data_path=args.processed_path,
        report_path=args.report_path,
        feature_set_version=args.feature_set_version,
    )
    print(json.dumps(training_report, indent=2, ensure_ascii=False))
