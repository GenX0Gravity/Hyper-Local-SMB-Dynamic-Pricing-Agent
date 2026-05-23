"""Pydantic schemas for forecasting API and pipelines."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float
    mape_pct: float
    demand_score_mae: float
    train_rows: int
    test_rows: int


class TrainRequest(BaseModel):
    lookback_days: int = Field(default=90, ge=7, le=365)
    force: bool = Field(default=False, description="Retrain even if a recent model exists")


class TrainResponse(BaseModel):
    tenant_id: UUID
    model_version: str
    trained_at: datetime
    metrics: EvaluationMetrics
    artifact_path: str
    message: str


class PredictRequest(BaseModel):
    product_id: Optional[UUID] = None
    at: Optional[datetime] = None
    weather: Optional[dict[str, Any]] = None
    footfall: Optional[dict[str, Any]] = None
    events: Optional[list[dict[str, Any]]] = None


class PredictResponse(BaseModel):
    tenant_id: UUID
    product_id: Optional[UUID] = None
    demand_score: float = Field(ge=0, le=100)
    predicted_units: float
    model_version: str
    confidence: float = Field(ge=0, le=1)
    top_features: dict[str, float] = Field(default_factory=dict)
    predicted_at: datetime


class MetricsResponse(BaseModel):
    tenant_id: UUID
    model_version: Optional[str] = None
    trained_at: Optional[datetime] = None
    metrics: Optional[EvaluationMetrics] = None
    has_model: bool


class BatchPredictResponse(BaseModel):
    tenant_id: UUID
    predictions: list[PredictResponse]
    model_version: str
