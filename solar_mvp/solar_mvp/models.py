"""ML model definitions for solar site scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


@dataclass
class ModelConfig:
    name: str
    model: Any
    description: str


LOGISTIC_REGRESSION = ModelConfig(
    name="logistic_regression",
    model=Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            C=1.0,
            random_state=42,
        )),
    ]),
    description="Logistic Regression with StandardScaler — coefficients → WEIGHTS_ML",
)

XGBOOST = ModelConfig(
    name="xgboost",
    model=XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=None,  # set dynamically based on class ratio
        eval_metric="aucpr",
        random_state=42,
    ),
    description="XGBoost — SHAP values for feature importance",
)


def get_lr_weights(fitted_pipeline: Pipeline, feature_names: list[str]) -> dict[str, float]:
    """Extract normalized weights from fitted LogisticRegression pipeline."""
    coefs = fitted_pipeline.named_steps["clf"].coef_[0]
    abs_sum = float(np.abs(coefs).sum())
    if abs_sum > 0:
        normalized = coefs / abs_sum
    else:
        normalized = coefs
    return dict(zip(feature_names, normalized.tolist()))
