"""Pydantic schemas for Event Intelligence Engine."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    IPL_MATCH = "ipl_match"
    FOOTBALL_MATCH = "football_match"
    DURGA_PUJA = "durga_puja"
    COLLEGE_FESTIVAL = "college_festival"
    PUBLIC_HOLIDAY = "public_holiday"
    LOCAL_EVENT = "local_event"
    UNKNOWN = "unknown"


class EventSource(str, Enum):
    PREDICTHQ = "predicthq"
    NEWSAPI = "newsapi"
    GOOGLE_TRENDS = "google_trends"
    MOCK = "mock"


class RawEventRecord(BaseModel):
    """Normalized event from any upstream source before classification."""

    external_id: str
    name: str
    description: str = ""
    raw_category: str = ""
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    attendance_est: int = 0
    distance_km: float = 1.0
    venue_name: str = ""
    source: EventSource
    trend_interest: float = 0.0  # 0–100 Google Trends interest
    news_sentiment: str = "neutral"  # positive | negative | neutral
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ClassifiedEvent(BaseModel):
    """Event after classification and impact scoring."""

    external_id: str
    name: str
    category: EventCategory
    category_label: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    attendance_est: int = 0
    distance_km: float = 1.0
    venue_name: str = ""
    source: EventSource
    impact_score: float = Field(ge=0.0, le=100.0, description="Event Impact Score 0–100")
    impact_factors: dict[str, float] = Field(default_factory=dict)
    classification_confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    trend_interest: float = 0.0
    news_sentiment: str = "neutral"
    hours_until_start: Optional[float] = None
    is_active: bool = False


class CategoryImpactSummary(BaseModel):
    category: EventCategory
    event_count: int
    max_impact_score: float
    total_attendance: int


class DemandAdjustment(BaseModel):
    metric: str
    baseline_score: float = 50.0
    adjusted_score: float
    delta_pct: float
    reason: str


class EventAlert(BaseModel):
    severity: str  # info | warning | critical
    code: str
    message: str
    related_event_id: Optional[str] = None


class EventIntelligenceReport(BaseModel):
    tenant_id: Optional[str] = None
    location: dict[str, float]
    events: list[ClassifiedEvent] = Field(default_factory=list)
    aggregate_impact_score: float = Field(
        0.0, ge=0.0, le=100.0, description="Composite Event Impact Score"
    )
    category_summary: list[CategoryImpactSummary] = Field(default_factory=list)
    demand_adjustments: list[DemandAdjustment] = Field(default_factory=list)
    alerts: list[EventAlert] = Field(default_factory=list)
    rules_fired: list[str] = Field(default_factory=list)
    sources_queried: list[str] = Field(default_factory=list)
    pipeline_stats: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    cache_hit: bool = False
