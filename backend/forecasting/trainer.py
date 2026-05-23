"""XGBoost training pipeline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sqlmodel import Session
from xgboost import XGBRegressor

from backend.core.config import settings
from backend.forecasting.dataset import build_training_dataframe
from backend.forecasting.evaluator import evaluate_predictions
from backend.forecasting.features import FEATURE_COLUMNS, TARGET_COLUMN, dataframe_to_xy
from backend.forecasting.model_store import ModelArtifact, ModelStore
from backend.forecasting.schemas import EvaluationMetrics, TrainResponse
from backend.models.forecast_model import ForecastModelRun

logger = logging.getLogger(__name__)


def _default_xgb_params() -> dict:
    return {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.08,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "reg:squarederror",
        "random_state": 42,
        "n_jobs": -1,
    }


class ForecastTrainer:
    def __init__(self, store: ModelStore | None = None):
        self.store = store or ModelStore()

    def train(
        self,
        session: Session,
        tenant_id: UUID,
        lookback_days: int = 90,
        force: bool = False,
        product_id: UUID | None = None,
    ) -> TrainResponse:
        if not force and self._recent_model_exists(session, tenant_id):
            artifact = self.store.load(tenant_id)
            if artifact:
                return TrainResponse(
                    tenant_id=tenant_id,
                    model_version=artifact.metadata.get("version", "unknown"),
                    trained_at=datetime.fromisoformat(
                        artifact.metadata["trained_at"].replace("Z", "+00:00")
                    ),
                    metrics=artifact.metrics,
                    artifact_path=artifact.metadata.get("model_path", ""),
                    message="Skipped — model trained within retrain window. Use force=true.",
                )

        df = build_training_dataframe(
            session, tenant_id, lookback_days=lookback_days, product_id=product_id
        )
        if len(df) < settings.FORECAST_MIN_TRAINING_ROWS:
            raise ValueError(
                f"Insufficient training rows ({len(df)}). "
                f"Need at least {settings.FORECAST_MIN_TRAINING_ROWS}."
            )

        scale_min = float(df["scale_min"].iloc[0])
        scale_max = float(df["scale_max"].iloc[0])

        x, y = dataframe_to_xy(df)
        split = settings.FORECAST_TRAIN_TEST_SPLIT
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=split, shuffle=False
        )

        model = XGBRegressor(**_default_xgb_params())
        model.fit(
            x_train,
            y_train,
            eval_set=[(x_test, y_test)],
            verbose=False,
        )

        y_pred = model.predict(x_test)
        metrics = evaluate_predictions(
            y_test,
            y_pred,
            scale_min,
            scale_max,
            train_rows=len(x_train),
            test_rows=len(x_test),
        )

        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_path = self.store.tenant_dir(tenant_id) / f"{version}_model.joblib"
        metadata = {
            "version": version,
            "tenant_id": str(tenant_id),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": lookback_days,
            "scale_min": scale_min,
            "scale_max": scale_max,
            "feature_columns": FEATURE_COLUMNS,
            "product_id": str(product_id) if product_id else None,
            "model_path": str(model_path),
        }
        self.store.save(tenant_id, model, metadata, metrics, version=version)

        run = ForecastModelRun(
            tenant_id=tenant_id,
            version=version,
            metrics_json=metrics.model_dump(),
            artifact_path=str(model_path),
            train_rows=metrics.train_rows,
            test_rows=metrics.test_rows,
            scale_min=scale_min,
            scale_max=scale_max,
        )
        session.add(run)
        session.commit()

        return TrainResponse(
            tenant_id=tenant_id,
            model_version=version,
            trained_at=datetime.now(timezone.utc),
            metrics=metrics,
            artifact_path=str(model_path),
            message="Model trained successfully.",
        )

    def _recent_model_exists(self, session: Session, tenant_id: UUID) -> bool:
        from datetime import timedelta
        from sqlmodel import select

        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.FORECAST_RETRAIN_DAYS)
        runs = session.exec(
            select(ForecastModelRun).where(ForecastModelRun.tenant_id == tenant_id)
        ).all()
        if runs:
            latest = max(runs, key=lambda r: r.trained_at)
            if latest.trained_at >= cutoff:
                return True
        return self.store.has_model(tenant_id)
