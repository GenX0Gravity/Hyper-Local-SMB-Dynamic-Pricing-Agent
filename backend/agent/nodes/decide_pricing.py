"""Node 3: Decide pricing actions from demand forecasts and feedback."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.agent.state import (
    AgentPhase,
    DemandForecast,
    FeedbackSnapshot,
    PricingAgentState,
    PricingRecommendation,
    RecommendationType,
    SignalBundle,
)

logger = logging.getLogger(__name__)


def decide_pricing_node(state: PricingAgentState) -> dict:
    logger.info("Agent[%s]: deciding pricing", state.get("run_id"))
    forecasts: list[DemandForecast] = state.get("forecasts") or []
    feedback: FeedbackSnapshot = state.get("feedback") or FeedbackSnapshot()
    catalog = state.get("product_catalog") or []
    signals: SignalBundle = state.get("signals") or SignalBundle()
    cap = feedback.preferred_discount_cap_pct

    catalog_by_id = {str(p["id"]): p for p in catalog}
    recs: list[PricingRecommendation] = []
    now = datetime.now(timezone.utc)

    # Location-level happy hour when traffic is low
    footfall = signals.footfall or {}
    if footfall.get("busy_percent", 100) < 35:
        recs.append(
            PricingRecommendation(
                recommendation_type=RecommendationType.HAPPY_HOUR,
                title="Happy Hour — drive afternoon traffic",
                description=(
                    f"Foot traffic at {footfall.get('busy_percent', 0)}% capacity. "
                    "Run 15–20% off beverages for next 3 hours."
                ),
                adjustment_pct=-15.0,
                valid_from=now,
                valid_until=now + timedelta(hours=3),
                priority=80,
                metadata={"trigger": "low_footfall"},
            )
        )

    # Bundle when event + high demand index
    events = signals.events or []
    if events and any(e.get("attendance", 0) >= 1000 for e in events):
        beverage_ids = [
            UUID(str(p["id"]))
            for p in catalog
            if (p.get("category") or "").lower() in ("beverage", "drinks", "coffee")
        ][:3]
        if len(beverage_ids) >= 2:
            recs.append(
                PricingRecommendation(
                    recommendation_type=RecommendationType.BUNDLE,
                    product_ids=beverage_ids,
                    title="Event Day Combo Bundle",
                    description="Bundle 2–3 top beverages at 10% below individual total.",
                    adjustment_pct=-10.0,
                    valid_from=now,
                    valid_until=now + timedelta(hours=8),
                    priority=70,
                    metadata={"trigger": "local_event"},
                )
            )

    for forecast in forecasts:
        if not forecast.product_id:
            continue
        product = catalog_by_id.get(str(forecast.product_id))
        if not product:
            continue

        current = float(product.get("current_price", product.get("base_price", 0)))
        min_p = product.get("min_price")
        max_p = product.get("max_price")
        idx = forecast.demand_index

        if idx < 0.85:
            discount = min(cap, max(5.0, (1 - idx) * 30))
            new_price = round(current * (1 - discount / 100), 2)
            if min_p is not None:
                new_price = max(float(min_p), new_price)
            recs.append(
                PricingRecommendation(
                    recommendation_type=RecommendationType.DISCOUNT,
                    product_ids=[forecast.product_id],
                    title=f"Discount — {product.get('name', 'product')}",
                    description=(
                        f"Demand index {idx:.2f}. Suggest {discount:.0f}% reduction "
                        f"to stimulate sales."
                    ),
                    adjustment_pct=-discount,
                    suggested_price=new_price,
                    previous_price=current,
                    valid_until=now + timedelta(hours=12),
                    priority=60,
                )
            )
        elif idx > 1.15:
            increase = min(15.0, (idx - 1) * 25)
            new_price = round(current * (1 + increase / 100), 2)
            if max_p is not None:
                new_price = min(float(max_p), new_price)
            recs.append(
                PricingRecommendation(
                    recommendation_type=RecommendationType.PRICE_INCREASE,
                    product_ids=[forecast.product_id],
                    title=f"Price Increase — {product.get('name', 'product')}",
                    description=(
                        f"Demand index {idx:.2f}. Capture margin with "
                        f"+{increase:.0f}% while demand is high."
                    ),
                    adjustment_pct=increase,
                    suggested_price=new_price,
                    previous_price=current,
                    valid_until=now + timedelta(hours=6),
                    priority=75,
                )
            )

    recs.sort(key=lambda r: r.priority, reverse=True)
    return {"phase": AgentPhase.DECIDE_PRICING, "recommendations": recs}
