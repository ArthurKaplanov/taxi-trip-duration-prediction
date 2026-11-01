"""Feature engineering for taxi trip duration models."""

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from taxi_trip_duration.config import FEATURE_SET_VERSION, FEATURE_SETS

BASE_REQUIRED_COLUMNS = [
    "PULocationID",
    "DOLocationID",
    "request_datetime",
]


def _require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def enrich_taxi_zones(
    df: pd.DataFrame,
    zone_lookup: pd.DataFrame,
) -> pd.DataFrame:
    processed = df.merge(
        zone_lookup.rename(
            columns={
                "LocationID": "PULocationID",
                "Borough": "pickup_borough",
                "Zone": "pickup_zone",
            }
        ),
        on="PULocationID",
        how="left",
    )
    processed = processed.merge(
        zone_lookup.rename(
            columns={
                "LocationID": "DOLocationID",
                "Borough": "dropoff_borough",
                "Zone": "dropoff_zone",
            }
        ),
        on="DOLocationID",
        how="left",
    )
    return processed


def build_features(
    df: pd.DataFrame,
    zone_lookup: pd.DataFrame,
    feature_set_version: str = FEATURE_SET_VERSION,
    select_feature_set: bool = False,
) -> pd.DataFrame:
    """Return a dataframe with engineered features added.

    If ``select_feature_set`` is true, only columns from the configured feature
    set are returned. Otherwise the original columns are preserved.
    """
    if feature_set_version not in FEATURE_SETS:
        raise ValueError(f"Unknown feature set version: {feature_set_version}")

    _require_columns(df, BASE_REQUIRED_COLUMNS)
    if not is_datetime64_any_dtype(df["request_datetime"]):
        raise TypeError("Column must be datetime: request_datetime")

    result = df.copy()

    result = enrich_taxi_zones(result, zone_lookup)

    result["route_id"] = (
        result["PULocationID"].astype(str) + "_" + result["DOLocationID"].astype(str)
    )
    result["request_hour"] = result["request_datetime"].dt.hour
    result["day_of_week"] = result["request_datetime"].dt.dayofweek
    result["is_weekend"] = (result["day_of_week"] >= 5).astype(int)
    result["same_zone"] = (result["PULocationID"] == result["DOLocationID"]).astype(int)
    result["route_id"] = (
        result["PULocationID"].astype(str) + "_" + result["DOLocationID"].astype(str)
    )

    if select_feature_set:
        feature_columns = FEATURE_SETS[feature_set_version]
        _require_columns(result, feature_columns)
        return result[feature_columns].copy()

    return result
