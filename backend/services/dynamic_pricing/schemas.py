"""Schemas for Dynamic Pricing Engine inputs and outputs."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PricingActionType(str, Enum):
    DISCOUNT = "discount"
    PRICE_INCREASE = "price_increase"
    HOLD = "hold"
    BUNDLE = "bundle"
    HAPPY_HOUR = "happy_hour"


class PricingInputs(BaseModel):
    """Signals fed into the pricing algorithm."""

    demand_score: float = Field(50.0, ge=0.0, le=100.0, description="0–100 demand index")
    inventory_level: int = Field(0, ge=0, description="Units in stock")
    inventory_score: float = Field(
        50.0, ge=0.0, le=100.0, description="Normalized scarcity 0=overstock, 100=scarce"
    )
    event_score: float = Field(0.0, ge=0.0, le=100.0)
    weather_score: float = Field(50.0, ge=0.0, le=100.0)
    business_rule_boost_pct: float = Field(
        0.0, description="Net % adjustment from matched business rules"
    )
    business_rules_matched: list[str] = Field(default_factory=list)


class BundleOffer(BaseModel):
    offer_id: str
    title: str
    description: str
    primary_category: str
    discount_pct: float = 0.0
    valid_hours: int = 6
    trigger: str


class HappyHourCampaign(BaseModel):
    campaign_id: str
    title: str
    description: str
    discount_pct: float
    hour_start: int
    hour_end: int
    days_of_week: list[int] = Field(default_factory=list)
    trigger: str


class ExplanationStep(BaseModel):
    factor: str
    value: float | str
    impact: str
    detail: str


class ProductPricingDecision(BaseModel):
    """Complete pricing output for one product."""

    product_id: UUID
    product_name: str
    sku: Optional[str] = None
    category: Optional[str] = None

    base_price: float
    current_price: float
    recommended_price: float
    cost_price: float

    discount_pct: float = Field(0.0, ge=0.0, le=100.0)
    price_increase_pct: float = Field(0.0, ge=0.0)
    bundle_offer: Optional[BundleOffer] = None
    happy_hour: Optional[HappyHourCampaign] = None

    action_type: PricingActionType = PricingActionType.HOLD
    pricing_pressure: float = Field(description="Composite signal -1 to +1")
    margin_pct: float = Field(description="Margin % at recommended price")
    margin_floor_pct: float
    constraints_applied: list[str] = Field(default_factory=list)
    explanations: list[ExplanationStep] = Field(default_factory=list)
    summary: str = ""


class DynamicPricingReport(BaseModel):
    tenant_id: UUID
    generated_at: datetime
    inputs_snapshot: dict[str, Any]
    decisions: list[ProductPricingDecision] = Field(default_factory=list)
    catalog_summary: dict[str, Any] = Field(default_factory=dict)
