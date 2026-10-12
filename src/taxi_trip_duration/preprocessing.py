import pandas as pd

from taxi_trip_duration.validation import calculate_duration_sec


def preprocess_trips(
    df: pd.DataFrame,
    model_input_columns: list[str],
    invalid_mask: pd.Series,
) -> pd.DataFrame:
    processed = df.loc[~invalid_mask, model_input_columns].copy()

    processed["target_duration_sec"] = calculate_duration_sec(df.loc[~invalid_mask])
    processed["route_id"] = (
        processed["PULocationID"].astype(str)
        + "->"
        + processed["DOLocationID"].astype(str)
    )
    processed["request_hour"] = processed["request_datetime"].dt.hour
    processed["request_dayofweek"] = processed["request_datetime"].dt.dayofweek

    return processed
