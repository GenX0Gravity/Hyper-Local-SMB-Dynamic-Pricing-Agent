"""Analytics module schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class KPIMetrics(BaseModel):
    revenue_increase: float = Field(description="Incremental revenue from dynamic pricing ($)")
    revenue_increase_pct: float = Field(description="% lift vs baseline revenue")
    conversion_rate: float = Field(ge=0, le=100, description="Accepted / decided recommendations %")
    accepted_recommendations: int = 0
    rejected_recommendations: int = 0
    pending_recommendations: int = 0
    demand_accuracy: float = Field(ge=0, le=100, description="Forecast vs actual demand accuracy %")
    event_impact_accuracy: float = Field(
        ge=0, le=100, description="Event impact prediction accuracy %"
    )
    total_revenue: float = 0.0
    total_units_sold: int = 0
    baseline_revenue: float = 0.0


class KPITrendPoint(BaseModel):
    date: str
    revenue_increase: float
    conversion_rate: float
    accepted: int
    rejected: int
    demand_accuracy: float
    event_impact_accuracy: float


class KPIDashboard(BaseModel):
    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    kpis: KPIMetrics
    trends: list[KPITrendPoint] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class PeriodReport(BaseModel):
    id: Optional[UUID] = None
    tenant_id: UUID
    period_type: str
    period_start: datetime
    period_end: datetime
    label: str
    kpis: KPIMetrics
    summary: str
    sections: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


class ReportsBundle(BaseModel):
    period_type: str
    reports: list[PeriodReport]
    aggregate: Optional[KPIMetrics] = None
