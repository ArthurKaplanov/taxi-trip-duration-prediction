"""Simple training pipeline for the taxi trip duration model."""

import argparse
import datetime
import json
from pathlib import Path

import mlflow
import mlflow.catboost
import mlflow.data
import pandas as pd
from loguru import logger
from mlflow.client import MlflowClient
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature

from taxi_trip_duration.config import (
    EXPERIMENT_NAME,
    FEATURE_SET_VERSION,
    FEATURE_SETS,
    MLFLOW_TRACKING_SERVER,
    PROCESSED_DATA_PATH,
    TARGET_COLUMN,
    TRAINING_REPORT_PATH,
    ZONE_LOOKUP_PATH,
)
from taxi_trip_duration.features_engineering import build_features
from taxi_trip_duration.train import (
    calculate_metrics,
    time_split,
    train_catboost_regressor,
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


def get_champion(client: MlflowClient, model_name: str):
    try:
        return client.get_model_version_by_alias(
            name=model_name,
            alias="Champion",
        )
    except MlflowException as exc:
        if exc.error_code == "RESOURCE_DOES_NOT_EXIST":
            return None
        raise


def compare_and_promote(
    model_name: str,
    challenger_model_uri: str,
    X_val,
    y_val,
    min_improvement: float = 0.0,
):
    client = MlflowClient()

    champion = get_champion(client, model_name)

    challenger_model = mlflow.pyfunc.load_model(challenger_model_uri)
    challenger_predictions = challenger_model.predict(X_val)

    challenger_mae = calculate_metrics(y_val, challenger_predictions)["mae"]

    if champion is None:
        # Bootstrap: первая модель
        registered = mlflow.register_model(
            model_uri=challenger_model_uri,
            name=model_name,
        )

        client.set_registered_model_alias(
            name=model_name,
            alias="Champion",
            version=registered.version,
        )

        return {
            "decision": "initial_champion",
            "version": registered.version,
            "challenger_mae": challenger_mae,
        }

    champion_model = mlflow.pyfunc.load_model(
        f"models:/{model_name}/{champion.version}"
    )

    champion_predictions = champion_model.predict(X_val)

    champion_mae = calculate_metrics(y_val, champion_predictions)["mae"]

    if challenger_mae < champion_mae - min_improvement:
        registered = mlflow.register_model(
            model_uri=challenger_model_uri,
            name=model_name,
        )

        client.set_registered_model_alias(
            name=model_name,
            alias="Champion",
            version=registered.version,
        )

        return {
            "decision": "promoted",
            "version": registered.version,
            "champion_mae": champion_mae,
            "challenger_mae": challenger_mae,
        }

    return {
        "decision": "rejected",
        "version": champion.version,
        "champion_mae": champion_mae,
        "challenger_mae": challenger_mae,
    }


def run_training_pipeline(
    processed_data_path: Path = PROCESSED_DATA_PATH,
    zone_lookup_path: Path = ZONE_LOOKUP_PATH,
    report_path: Path = TRAINING_REPORT_PATH,
    feature_set_version: str = FEATURE_SET_VERSION,
) -> dict:

    mlflow.set_tracking_uri(MLFLOW_TRACKING_SERVER)
    mlflow.set_experiment(EXPERIMENT_NAME)

    RUN_NAME = f"taxi_catboost_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info("Starting MLflow run")

    with mlflow.start_run(run_name=RUN_NAME):
        try:
            mlflow.set_tags(
                {"features_version": feature_set_version, "model_type": "catboost"}
            )
            df = pd.read_parquet(processed_data_path)

            df_zone_lookup = pd.read_csv(zone_lookup_path)
            df_zone_lookup = df_zone_lookup.fillna("Unknown")
            df_zone_lookup = df_zone_lookup[["LocationID", "Borough", "Zone"]]

            df = build_features(df, df_zone_lookup)

            df.to_parquet("data/processed/fhvhv_tripdata_2026-05_test.parquet")

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

            catboost_model = train_catboost_regressor(
                X_train,
                y_train,
                cat_features=cat_features,
                X_val=X_val,
                y_val=y_val,
            )
            input_example = X_train.head(5)
            signature = infer_signature(
                input_example,
                catboost_model.predict(input_example),
            )

            model_catboost_info = mlflow.catboost.log_model(
                cb_model=catboost_model,
                name="model",
                signature=signature,
                input_example=input_example,
            )

            data_eval = pd.DataFrame(X_val)
            data_eval["target"] = y_val

            mlflow.models.evaluate(
                model=model_catboost_info.model_uri,
                data=data_eval,
                targets="target",
                model_type="regressor",
                evaluator_config={"log_model_explainability": False},
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
                    "val": calculate_metrics(y_val, catboost_val_pred),
                    "test": calculate_metrics(y_test, catboost_test_pred),
                },
            }
            mlflow.log_dict(report, "reports/training_metrics.json")

            mlflow.log_params(
                {
                    "feature_set_version": feature_set_version,
                    "train_rows": len(train_df),
                    "val_rows": len(val_df),
                    "test_rows": len(test_df),
                    **catboost_model.get_params(),
                }
            )

            mlflow.log_dict(
                {
                    "feature_set_version": feature_set_version,
                    "feature_columns": feature_columns,
                    "categorical_features": cat_features,
                    "target": TARGET_COLUMN,
                },
                "config/feature_config.json",
            )

            mlflow.log_dict(
                {
                    "train_start": str(train_df["request_datetime"].min()),
                    "train_end": str(train_df["request_datetime"].max()),
                    "val_start": str(val_df["request_datetime"].min()),
                    "val_end": str(val_df["request_datetime"].max()),
                },
                "config/data_split.json",
            )

            dataset = mlflow.data.from_pandas(
                train_df,
                name="fhvhv_train",
                source=str(processed_data_path),
                targets=TARGET_COLUMN,
            )

            mlflow.log_input(dataset, context="training")

            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            decision = compare_and_promote(
                model_name=f"{EXPERIMENT_NAME}_model",
                challenger_model_uri=model_catboost_info.model_uri,
                X_val=X_val,
                y_val=y_val,
                min_improvement=5.0,
            )

            mlflow.log_dict(
                decision,
                "reports/promotion_decision.json",
            )

            logger.info(f"Promotion decision: {decision}")

            return report
        except Exception as ex:
            logger.exception(f"Error during MLflow run: {str(ex)}")
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-path", type=Path, default=PROCESSED_DATA_PATH)
    parser.add_argument("--zone-lookup-path", type=Path, default=ZONE_LOOKUP_PATH)
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
