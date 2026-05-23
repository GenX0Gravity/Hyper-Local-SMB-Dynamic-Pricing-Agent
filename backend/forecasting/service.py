"""Facade for training, prediction, and retraining."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from backend.forecasting.model_store import ModelStore
from backend.forecasting.predictor import DemandPredictor
from backend.forecasting.schemas import (
    BatchPredictResponse,
    MetricsResponse,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
)
from backend.forecasting.trainer import ForecastTrainer
from backend.models.forecast_model import ForecastModelRun


class DemandForecastingService:
    def __init__(self):
        self.store = ModelStore()
        self.trainer = ForecastTrainer(self.store)
        self.predictor = DemandPredictor(self.store)

    def train(
        self, session: Session, tenant_id: UUID, request: TrainRequest
    ) -> TrainResponse:
        return self.trainer.train(
            session,
            tenant_id,
            lookback_days=request.lookback_days,
            force=request.force,
        )

    def retrain(
        self, session: Session, tenant_id: UUID, lookback_days: int = 90
    ) -> TrainResponse:
        """Retraining pipeline — always forces a new model version."""
        return self.trainer.train(
            session,
            tenant_id,
            lookback_days=lookback_days,
            force=True,
        )

    async def predict(
        self,
        session: Session,
        tenant_id: UUID,
        request: PredictRequest,
    ) -> PredictResponse:
        return await self.predictor.predict(
            session,
            tenant_id,
            product_id=request.product_id,
            at=request.at,
            weather=request.weather,
            footfall=request.footfall,
            events=request.events,
        )

    async def predict_batch(
        self, session: Session, tenant_id: UUID, at: Optional[datetime] = None
    ) -> BatchPredictResponse:
        return await self.predictor.predict_catalog(session, tenant_id, at=at)

    def get_metrics(self, session: Session, tenant_id: UUID) -> MetricsResponse:
        artifact = self.store.load(tenant_id)
        if artifact:
            trained_at = datetime.fromisoformat(
                str(artifact.metadata.get("trained_at", "")).replace("Z", "+00:00")
            )
            return MetricsResponse(
                tenant_id=tenant_id,
                model_version=artifact.metadata.get("version"),
                trained_at=trained_at,
                metrics=artifact.metrics,
                has_model=True,
            )

        runs = session.exec(
            select(ForecastModelRun).where(ForecastModelRun.tenant_id == tenant_id)
        ).all()
        latest_run = max(runs, key=lambda r: r.trained_at) if runs else None

        if latest_run:
            from backend.forecasting.schemas import EvaluationMetrics

            return MetricsResponse(
                tenant_id=tenant_id,
                model_version=latest_run.version,
                trained_at=latest_run.trained_at,
                metrics=EvaluationMetrics.model_validate(latest_run.metrics_json),
                has_model=False,
            )

        return MetricsResponse(tenant_id=tenant_id, has_model=False)


demand_forecasting_service = DemandForecastingService()
