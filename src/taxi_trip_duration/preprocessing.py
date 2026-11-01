import pandas as pd

from taxi_trip_duration.validation import calculate_duration_sec


def preprocess_trips(
    df: pd.DataFrame,
    model_input_columns: list[str],
    invalid_mask: pd.Series,
) -> pd.DataFrame:
    processed = df.loc[~invalid_mask, model_input_columns].copy()

    processed["target_duration_sec"] = calculate_duration_sec(df.loc[~invalid_mask])

    assert len(processed) == (~invalid_mask).sum()

    return processed
