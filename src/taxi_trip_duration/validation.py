import pandas as pd


def require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def calculate_duration_sec(df: pd.DataFrame) -> pd.Series:
    return (df["dropoff_datetime"] - df["pickup_datetime"]).dt.total_seconds()


def build_invalid_mask(
    df: pd.DataFrame,
    required_columns: list[str],
    known_location_ids: set[int] | None = None,
) -> pd.Series:
    duration_sec = calculate_duration_sec(df)

    invalid_mask = df[required_columns].isna().any(axis=1)
    invalid_mask |= duration_sec <= 0
    invalid_mask |= df["pickup_datetime"] < df["request_datetime"]

    if known_location_ids is not None:
        invalid_mask |= ~df["PULocationID"].isin(known_location_ids)
        invalid_mask |= ~df["DOLocationID"].isin(known_location_ids)

    return invalid_mask


def iqr_upper_outlier_mask(values: pd.Series) -> pd.Series:
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    upper_bound = q3 + 1.5 * iqr

    return values > upper_bound


def build_quality_report(
    df_raw: pd.DataFrame,
    df_processed: pd.DataFrame,
    dataset_name: str,
    required_columns: list[str],
    invalid_mask: pd.Series,
) -> dict:
    duration_raw = calculate_duration_sec(df_raw)
    duration_processed = df_processed["target_duration_sec"]

    return {
        "dataset": dataset_name,
        "rows_raw": len(df_raw),
        "rows_processed": len(df_processed),
        "rows_dropped": int(invalid_mask.sum()),
        "missing_rate": {
            col: float(df_raw[col].isna().mean()) for col in required_columns
        },
        "duplicate_row_count": int(df_raw.duplicated().sum()),
        "invalid_duration_count": int((duration_raw <= 0).sum()),
        "pickup_before_request_count": int(
            (df_raw["pickup_datetime"] < df_raw["request_datetime"]).sum()
        ),
        "duration_iqr_upper_outlier_count": int(
            iqr_upper_outlier_mask(duration_processed).sum()
        ),
        "duration_p50": float(duration_processed.quantile(0.50)),
        "duration_p95": float(duration_processed.quantile(0.95)),
    }
