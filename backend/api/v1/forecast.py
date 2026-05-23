"""Demand forecasting API — train, predict, retrain, metrics."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from backend.api.deps import get_current_tenant_id, get_db
from backend.forecasting.schemas import (
    BatchPredictResponse,
    MetricsResponse,
    PredictRequest,
    PredictResponse,
    TrainRequest,
    TrainResponse,
)
from backend.forecasting.service import demand_forecasting_service

router = APIRouter()


@router.post("/train", response_model=TrainResponse)
def train_forecast_model(
    body: TrainRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Training pipeline — fits XGBoost on historical sales + signals."""
    try:
        return demand_forecasting_service.train(db, tenant_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/retrain", response_model=TrainResponse)
def retrain_forecast_model(
    lookback_days: int = 90,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Retraining pipeline — always produces a new model version."""
    try:
        return demand_forecasting_service.retrain(db, tenant_id, lookback_days=lookback_days)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/predict", response_model=PredictResponse)
async def predict_demand(
    body: PredictRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Prediction API — returns demand score 0–100."""
    try:
        return await demand_forecasting_service.predict(db, tenant_id, body)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/predict/batch", response_model=BatchPredictResponse)
async def predict_demand_batch(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Batch prediction for all products in catalog."""
    try:
        return await demand_forecasting_service.predict_batch(db, tenant_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/metrics", response_model=MetricsResponse)
def get_forecast_metrics(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Evaluation metrics from the latest training run."""
    return demand_forecasting_service.get_metrics(db, tenant_id)
