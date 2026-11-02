"""Проверка согласованности training и serving признаков."""

import pandas as pd

from taxi_trip_duration.app import TripRequest
from taxi_trip_duration.config import (
    CATEGORICAL_FEATURES,
    FEATURE_SET_VERSION,
    FEATURE_SETS,
)
from taxi_trip_duration.features_engineering import build_features
from taxi_trip_duration.model_input import prepare_model_input


def test_training_serving_consistency():
    # 1. Небольшой справочник для изолированного теста.
    zone_lookup = pd.DataFrame(
        {
            "LocationID": [76, 161],
            "Borough": ["Brooklyn", "Manhattan"],
            "Zone": ["East New York", "Midtown Center"],
        }
    )

    # 2. Историческая запись для training.
    historical_trip = pd.DataFrame(
        [
            {
                "PULocationID": 76,
                "DOLocationID": 161,
                "request_datetime": pd.Timestamp("2026-05-15 08:30:00"),
                "hvfhs_license_num": "HV0003",
                "shared_request_flag": "N",
                "wav_request_flag": "N",
                "target_duration_sec": 1800.0,
            }
        ]
    )

    # 3. Тот же заказ через API Request Schema.
    payload = TripRequest.model_validate(
        {
            "PULocationID": 76,
            "DOLocationID": 161,
            "request_datetime": "2026-05-15T08:30:00",
            "hvfhs_license_num": "HV0003",
            "shared_request_flag": "N",
            "wav_request_flag": "N",
        }
    )

    serving_trip = pd.DataFrame([payload.model_dump()])

    def to_model_input(df: pd.DataFrame) -> pd.DataFrame:
        features = build_features(
            df,
            zone_lookup=zone_lookup,
        )
        return prepare_model_input(
            features,
            feature_columns=FEATURE_SETS[FEATURE_SET_VERSION],
            cat_features=CATEGORICAL_FEATURES,
        )

    # 4. Независимо подготавливаем входы.
    X_training = to_model_input(historical_trip)
    X_serving = to_model_input(serving_trip)

    # 5. Сравниваем значения, порядок колонок и dtype.
    pd.testing.assert_frame_equal(
        X_training,
        X_serving,
        check_dtype=True,
    )

    # 6. Дополнительно проверяем ожидаемую семантику.
    assert X_serving["route_id"].iloc[0] == "76_161"
    assert X_serving["request_hour"].iloc[0] == 8
    assert X_serving["day_of_week"].iloc[0] == 4
    assert X_serving["is_weekend"].iloc[0] == 0
    assert X_serving["same_zone"].iloc[0] == 0

    assert X_serving["pickup_borough"].iloc[0] == "Brooklyn"
    assert X_serving["dropoff_borough"].iloc[0] == "Manhattan"

    # Категориальные ID должны быть строками,
    # поскольку CatBoost обучался на строковых категориях.
    assert X_serving["PULocationID"].iloc[0] == "76"
    assert X_serving["DOLocationID"].iloc[0] == "161"

    # Target не должен попадать в модельный вход.
    assert "target_duration_sec" not in X_serving.columns
