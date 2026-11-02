import pandas as pd


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
