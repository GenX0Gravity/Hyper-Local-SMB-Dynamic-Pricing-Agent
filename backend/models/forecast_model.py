from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class ForecastModelRun(SQLModel, table=True):
    """Training run metadata persisted for retraining decisions."""

    __tablename__ = "forecast_model_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id", index=True)
    version: str = Field(max_length=32, index=True)
    trained_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    artifact_path: str = Field(max_length=512)
    train_rows: int = 0
    test_rows: int = 0
    scale_min: float = 0.0
    scale_max: float = 100.0
    is_active: bool = Field(default=True)
