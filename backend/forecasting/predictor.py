"""Inference pipeline — demand score 0–100."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from backend.forecasting.dataset import build_training_dataframe
from backend.forecasting.features import (
    FEATURE_COLUMNS,
    features_to_vector,
    row_to_features,
    units_to_demand_score,
)
from backend.forecasting.model_store import ModelStore
from backend.forecasting.schemas import BatchPredictResponse, PredictResponse
from backend.models.product import Product
from backend.models.tenant import Tenant
from backend.services.event_service import event_service
from backend.services.footfall_service import footfall_service
from backend.services.weather_service import weather_service

logger = logging.getLogger(__name__)


class DemandPredictor:
    def __init__(self, store: ModelStore | None = None):
        self.store = store or ModelStore()

    async def _live_signals(
        self, tenant: Tenant
    ) -> tuple[dict, dict, list]:
        weather, footfall, events = await asyncio.gather(
            weather_service.get_current_weather(tenant.latitude, tenant.longitude),
            footfall_service.get_popular_times(tenant.latitude, tenant.longitude),
            event_service.get_upcoming_events(tenant.latitude, tenant.longitude),
        )
        return weather, footfall, events

    def _lag_from_history(
        self, session: Session, tenant_id: UUID, at: datetime
    ) -> tuple[float, float, float, float]:
        df = build_training_dataframe(session, tenant_id, lookback_days=30)
        if df.empty:
            return 0.0, 0.0, 0.0, 0.0
        ts = pd.Timestamp(at)
        prior = df[df["ts"] <= ts] if "ts" in df.columns else df
        if prior.empty:
            row = df.iloc[-1]
        else:
            row = prior.iloc[-1]
        return (
            float(row.get("sales_lag_1h", 0)),
            float(row.get("sales_lag_24h", 0)),
            float(row.get("sales_rolling_7d_mean", 0)),
            float(row.get("sales_rolling_7d_std", 0)),
        )

    def _top_feature_importance(
        self, model, features: dict[str, float], top_k: int = 5
    ) -> dict[str, float]:
        try:
            imp = model.feature_importances_
            pairs = sorted(
                zip(FEATURE_COLUMNS, imp), key=lambda x: x[1], reverse=True
            )[:top_k]
            return {name: round(float(score), 4) for name, score in pairs}
        except Exception:
            return {k: round(features.get(k, 0.0), 4) for k in FEATURE_COLUMNS[:top_k]}

    async def predict(
        self,
        session: Session,
        tenant_id: UUID,
        product_id: UUID | None = None,
        at: datetime | None = None,
        weather: dict[str, Any] | None = None,
        footfall: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> PredictResponse:
        artifact = self.store.load(tenant_id)
        if artifact is None:
            raise FileNotFoundError(
                f"No trained model for tenant {tenant_id}. Call POST /forecast/train first."
            )

        tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        at = at or datetime.now(timezone.utc)
        if weather is None or footfall is None or events is None:
            live_w, live_f, live_e = await self._live_signals(tenant)
            weather = weather or live_w
            footfall = footfall or live_f
            events = events if events is not None else live_e

        lag_1h, lag_24h, roll_mean, roll_std = self._lag_from_history(
            session, tenant_id, at
        )
        feats = row_to_features(
            pd.Timestamp(at),
            weather=weather,
            footfall=footfall,
            events=events,
            sales_lag_1h=lag_1h,
            sales_lag_24h=lag_24h,
            sales_rolling_7d_mean=roll_mean,
            sales_rolling_7d_std=roll_std,
        )
        x = features_to_vector(feats).reshape(1, -1)
        units = float(artifact.model.predict(x)[0])
        scale_min = float(artifact.metadata.get("scale_min", 0))
        scale_max = float(artifact.metadata.get("scale_max", 100))
        score = units_to_demand_score(units, scale_min, scale_max)

        # Confidence from model R² and data freshness
        r2 = max(0.0, artifact.metrics.r2)
        confidence = round(min(0.95, 0.5 + r2 * 0.45), 2)

        return PredictResponse(
            tenant_id=tenant_id,
            product_id=product_id,
            demand_score=round(float(score), 2),
            predicted_units=round(units, 2),
            model_version=artifact.metadata.get("version", "unknown"),
            confidence=confidence,
            top_features=self._top_feature_importance(artifact.model, feats),
            predicted_at=at,
        )

    async def predict_catalog(
        self,
        session: Session,
        tenant_id: UUID,
        at: datetime | None = None,
    ) -> BatchPredictResponse:
        artifact = self.store.load(tenant_id)
        if artifact is None:
            raise FileNotFoundError(f"No trained model for tenant {tenant_id}")

        products = session.exec(
            select(Product).where(Product.tenant_id == tenant_id)
        ).all()

        base = await self.predict(session, tenant_id, at=at)
        predictions = []
        for product in products:
            p = base.model_copy(update={"product_id": product.id})
            predictions.append(p)

        if not predictions:
            predictions = [base]

        return BatchPredictResponse(
            tenant_id=tenant_id,
            predictions=predictions,
            model_version=artifact.metadata.get("version", "unknown"),
        )
