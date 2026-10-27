"""Training helpers for taxi trip duration models."""

import numpy as np
import pandas as pd


def time_split(
    df: pd.DataFrame,
    time_column: str = "request_datetime",
    train_size: float = 0.8,
    val_size: float = 0.1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Time-based split
    Описание: функция делит df на train val и test. сортировка по request_datetime
    train - до 80%
    val - с 81 до 90%
    test - с 91 до 100%
    return train, val, test
    """
    if time_column not in df.columns:
        raise ValueError(f"Missing time column: {time_column}")

    if not 0 < train_size < 1:
        raise ValueError("train_size must be between 0 and 1")
    if not 0 < val_size < 1:
        raise ValueError("val_size must be between 0 and 1")
    if train_size + val_size >= 1:
        raise ValueError("train_size + val_size must be less than 1")

    sorted_df = df.sort_values(time_column).reset_index(drop=True)
    train_end = int(len(sorted_df) * train_size)
    val_end = int(len(sorted_df) * (train_size + val_size))

    train_df = sorted_df.iloc[:train_end].copy()
    val_df = sorted_df.iloc[train_end:val_end].copy()
    test_df = sorted_df.iloc[val_end:].copy()

    return train_df, val_df, test_df


def train_dummy_regression(y_train: pd.Series):
    """обучение DummyRegressor с медианной стратегией
    всегда прогнозирует медианную длительность поездки, рассчитанную на Train
    """
    try:
        from sklearn.dummy import DummyRegressor
    except ImportError as exc:
        raise ImportError("Install scikit-learn to train DummyRegressor") from exc

    model = DummyRegressor(strategy="median")
    model.fit(np.zeros((len(y_train), 1)), y_train)

    return model


def train_catboost_regressor(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cat_features: list[str],
    X_val: pd.DataFrame | None = None,
    y_val: pd.Series | None = None,
):
    """обучение CatBoostRegressor
    route_id, hvfhs_license_num, зоны и borough передать в cat_features
    """
    try:
        from catboost import CatBoostRegressor
    except ImportError as exc:
        raise ImportError("Install catboost to train CatBoostRegressor") from exc

    model = CatBoostRegressor(
        iterations=300,
        learning_rate=0.1,
        depth=8,
        loss_function="RMSE",
        random_seed=42,
        allow_writing_files=False,
        verbose=False,
    )

    eval_set = None
    if X_val is not None and y_val is not None:
        eval_set = (X_val, y_val)

    model.fit(
        X_train,
        y_train,
        cat_features=cat_features,
        eval_set=eval_set,
    )

    return model


def calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    errors = np.asarray(y_true) - np.asarray(y_pred)

    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
    }
