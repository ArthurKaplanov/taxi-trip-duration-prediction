import pandas as pd

from taxi_trip_duration.validation import calculate_duration_sec


def preprocess_trips(
    df: pd.DataFrame,
    zone_lookup: pd.DataFrame,
    model_input_columns: list[str],
    invalid_mask: pd.Series,
) -> pd.DataFrame:
    processed = df.loc[~invalid_mask, model_input_columns].copy()
    zone_lookup = zone_lookup[["LocationID", "Borough", "Zone"]]

    processed["target_duration_sec"] = calculate_duration_sec(df.loc[~invalid_mask])

    processed = processed.merge(
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

    assert len(processed) == (~invalid_mask).sum()

    processed["route_id"] = (
        processed["PULocationID"].astype(str)
        + "_"
        + processed["DOLocationID"].astype(str)
    )

    return processed
