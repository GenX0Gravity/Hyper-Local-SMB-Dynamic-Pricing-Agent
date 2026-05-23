"""
LangGraph state definitions for the PricePulse pricing agent.

State is partitioned into reducers (append-only lists) and scalar fields
updated by each node in the pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

class AgentPhase(str, Enum):
    INIT = "init"
    COLLECT_SIGNALS = "collect_signals"
    PREDICT_DEMAND = "predict_demand"
    DECIDE_PRICING = "decide_pricing"
    NOTIFY_OWNER = "notify_owner"
    LEARN_FEEDBACK = "learn_feedback"
    COMPLETE = "complete"
    FAILED = "failed"


class RecommendationType(str, Enum):
    DISCOUNT = "discount"
    BUNDLE = "bundle"
    HAPPY_HOUR = "happy_hour"
    PRICE_INCREASE = "price_increase"


class SignalBundle(BaseModel):
    """Normalized external signals for one location."""

    weather: Optional[dict[str, Any]] = None
    footfall: Optional[dict[str, Any]] = None
    news: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    sales_summary: Optional[dict[str, Any]] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    sources_ok: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)


class DemandForecast(BaseModel):
    model_config = {"protected_namespaces": ()}

    location_id: UUID
    product_id: Optional[UUID] = None
    horizon_hours: int = 24
    demand_index: float = Field(ge=0, le=2, description="1.0 = baseline")
    confidence: float = Field(ge=0, le=1, default=0.7)
    drivers: list[str] = Field(default_factory=list)
    model_version: str = "heuristic-v1"


class PricingRecommendation(BaseModel):
    recommendation_type: RecommendationType
    product_ids: list[UUID] = Field(default_factory=list)
    title: str
    description: str
    adjustment_pct: float = 0.0
    suggested_price: Optional[float] = None
    previous_price: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    priority: int = 50
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentError(BaseModel):
    node: str
    tool: Optional[str] = None
    message: str
    recoverable: bool = True
    attempt: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FeedbackSnapshot(BaseModel):
    """Owner responses used for learning."""

    approved_count: int = 0
    rejected_count: int = 0
    top_rejection_reasons: list[str] = Field(default_factory=list)
    preferred_discount_cap_pct: float = 15.0


def merge_errors(
    left: list[AgentError], right: list[AgentError]
) -> list[AgentError]:
    return left + right


def merge_recommendations(
    left: list[PricingRecommendation], right: list[PricingRecommendation]
) -> list[PricingRecommendation]:
    return left + right


class PricingAgentState(TypedDict, total=False):
    """
    LangGraph shared state passed between nodes.

    Reducers:
      - errors: append
      - recommendations: append
    """

    # Run context
    run_id: str
    business_id: UUID
    location_id: UUID
    triggered_by: str  # celery | api | manual

    # Store context (loaded at start)
    business_name: str
    latitude: float
    longitude: float
    timezone: str
    currency: str
    whatsapp_phone: Optional[str]
    whatsapp_enabled: bool
    product_catalog: list[dict[str, Any]]

    # Pipeline artifacts
    phase: AgentPhase
    signals: SignalBundle
    forecasts: list[DemandForecast]
    recommendations: Annotated[list[PricingRecommendation], merge_recommendations]
    notification_sent: bool
    notification_body: Optional[str]

    # Memory keys (resolved by memory layer)
    memory_session_key: str
    feedback: FeedbackSnapshot

    # Recovery
    retry_count: int
    max_retries: int
    use_cached_signals: bool
    errors: Annotated[list[AgentError], merge_errors]

    # Terminal
    completed_at: Optional[datetime]
