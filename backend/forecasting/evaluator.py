"""Evaluation metrics for demand forecasting models."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from backend.forecasting.features import units_to_demand_score
from backend.forecasting.schemas import EvaluationMetrics


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scale_min: float,
    scale_max: float,
    train_rows: int,
    test_rows: int,
) -> EvaluationMetrics:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0

    with np.errstate(divide="ignore", invalid="ignore"):
        mape = np.abs((y_true - y_pred) / np.maximum(y_true, 1e-6)) * 100
    mape_pct = float(np.nanmean(mape)) if len(mape) else 0.0

    true_scores = units_to_demand_score(y_true, scale_min, scale_max)
    pred_scores = units_to_demand_score(y_pred, scale_min, scale_max)
    demand_score_mae = float(mean_absolute_error(true_scores, pred_scores))

    return EvaluationMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        r2=round(r2, 4),
        mape_pct=round(mape_pct, 2),
        demand_score_mae=round(demand_score_mae, 2),
        train_rows=train_rows,
        test_rows=test_rows,
    )
