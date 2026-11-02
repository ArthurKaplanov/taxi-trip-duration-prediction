import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

import mlflow
import pandas as pd
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from taxi_trip_duration.config import (
    CATEGORICAL_FEATURES,
    FEATURE_SET_VERSION,
    FEATURE_SETS,
    MLFLOW_TRACKING_SERVER,
    MODEL_URI,
    ZONE_LOOKUP_PATH,
)
from taxi_trip_duration.features_engineering import build_features
from taxi_trip_duration.model_contract import ModelContract, validate_model_contract
from taxi_trip_duration.model_input import prepare_model_input


class TripRequest(BaseModel):
    PULocationID: int = Field(gt=0)
    DOLocationID: int = Field(gt=0)
    request_datetime: datetime
    hvfhs_license_num: str
    shared_request_flag: Literal["Y", "N"]
    wav_request_flag: Literal["Y", "N"]


class PredictionOutput(BaseModel):
    predicted_duration_sec: float
    model_version: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    mlflow.set_tracking_uri(MLFLOW_TRACKING_SERVER)

    # Загружаем модель один раз при старте приложения.
    app.state.model = mlflow.pyfunc.load_model(MODEL_URI)

    print(MODEL_URI)
    if not app.state.model.metadata.metadata:
        raise RuntimeError("Model has no serving contract metadata")

    expected = ModelContract(
        feature_set_version=app.state.model.metadata.metadata["feature_set_version"],
        feature_columns=app.state.model.metadata.metadata["feature_columns"],
        categorical_features=app.state.model.metadata.metadata["categorical_features"],
    )

    actual = ModelContract(
        feature_set_version=FEATURE_SET_VERSION,
        feature_columns=FEATURE_SETS[FEATURE_SET_VERSION],
        categorical_features=[
            col
            for col in CATEGORICAL_FEATURES
            if col in FEATURE_SETS[FEATURE_SET_VERSION]
        ],
    )

    validate_model_contract(expected, actual)

    # Загружаем справочник зон один раз.
    df_zone_lookup = pd.read_csv(ZONE_LOOKUP_PATH)
    df_zone_lookup = df_zone_lookup.fillna("Unknown")
    df_zone_lookup = df_zone_lookup[["LocationID", "Borough", "Zone"]]
    app.state.zone_lookup = df_zone_lookup

    yield

    app.state.model = None
    app.state.zone_lookup = None


app = FastAPI(
    title="Taxi prediction service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/predict", response_model=PredictionOutput)
def predict(payload: TripRequest, request: Request):
    df = pd.DataFrame([payload.model_dump()])

    # Предполагаем, что общая функция уже выполняет
    # lookup зон и остальные преобразования.
    df_features = build_features(
        df,
        zone_lookup=request.app.state.zone_lookup,
    )

    X = prepare_model_input(
        df_features,
        feature_columns=FEATURE_SETS[FEATURE_SET_VERSION],
        cat_features=CATEGORICAL_FEATURES,
    )

    predictions = request.app.state.model.predict(X)
    predicted_duration = float(predictions[0])

    if not math.isfinite(predicted_duration):
        raise RuntimeError("Model returned a non-finite prediction")

    return PredictionOutput(
        predicted_duration_sec=max(0.0, predicted_duration),
        model_version=MODEL_URI,
    )


@app.get("/health")
def health_check(request: Request):
    return {
        "status": "healthy",
        "model_loaded": request.app.state.model is not None,
        "timestamp": datetime.now(timezone.utc),
    }
