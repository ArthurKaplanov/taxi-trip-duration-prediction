from dataclasses import dataclass


@dataclass(frozen=True)
class ModelContract:
    feature_set_version: str
    feature_columns: list[str]
    categorical_features: list[str]


def validate_model_contract(
    expected: ModelContract,
    actual: ModelContract,
) -> None:
    if expected != actual:
        raise ValueError(
            "Model contract mismatch!\n"
            f"Model expects: {expected}\n"
            f"Serving provides: {actual}"
        )
