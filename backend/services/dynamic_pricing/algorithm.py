"""
Dynamic Pricing Algorithm

Combines demand, inventory, event, weather, and business-rule signals into:
  - discount_pct / price_increase_pct
  - bundle offers & happy hour campaigns

All adjustments pass margin-floor and max-discount constraints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.core.config import settings
from backend.models.product import Product
from backend.models.rule import PricingRule
from backend.services.dynamic_pricing.constraints import PricingConstraints
from backend.services.dynamic_pricing.explain import ExplanationBuilder
from backend.services.dynamic_pricing.offers import OfferGenerator
from backend.services.dynamic_pricing.schemas import (
    PricingActionType,
    PricingInputs,
    ProductPricingDecision,
)


class DynamicPricingAlgorithm:
    """
    Weighted signal fusion → pricing pressure → constrained price adjustment.

    Weights (configurable via settings):
      demand 35%, event 25%, weather 20%, inventory 20%
    Business rules apply additive % boost on top.
    """

    PRESSURE_INCREASE_THRESHOLD = 0.12
    PRESSURE_DISCOUNT_THRESHOLD = -0.12

    def __init__(
        self,
        constraints: PricingConstraints | None = None,
        offers: OfferGenerator | None = None,
        explainer: ExplanationBuilder | None = None,
    ):
        self.constraints = constraints or PricingConstraints()
        self.offers = offers or OfferGenerator()
        self.explainer = explainer or ExplanationBuilder()

    @staticmethod
    def inventory_score(stock_qty: int, baseline: int | None = None) -> float:
        """
        0 = overstocked (discount pressure), 100 = scarce (increase pressure).
        """
        baseline = baseline or settings.PRICING_INVENTORY_BASELINE_UNITS
        if stock_qty <= 0:
            return 95.0
        ratio = min(stock_qty / max(baseline, 1), 2.0)
        return round(max(0.0, min(100.0, 100.0 - (ratio * 50.0))), 1)

    @staticmethod
    def weather_score_from_signal(weather: dict[str, Any] | None) -> float:
        """Map weather intelligence / legacy dict to 0–100 score."""
        if not weather:
            return 50.0
        if "weather_score" in weather:
            return float(weather["weather_score"])
        score = 50.0
        if weather.get("is_heavy_rain"):
            score += 22.0
        elif weather.get("is_raining"):
            score += 12.0
        cond = str(weather.get("condition") or "").lower()
        if "clear" in cond or "sun" in cond:
            score += 8.0
        temp = float(weather.get("temp") or weather.get("temperature_c") or 20)
        if temp >= 32:
            score += 10.0
        if temp <= 5:
            score += 5.0
        return round(min(100.0, max(0.0, score)), 1)

    @staticmethod
    def event_score_from_signals(events: list[dict[str, Any]] | None) -> float:
        if not events:
            return 0.0
        impacts = [float(e.get("impact_score") or e.get("aggregate_impact_score") or 0) for e in events]
        if impacts:
            return round(min(100.0, max(impacts)), 1)
        attendances = [float(e.get("attendance") or e.get("attendance_est") or 0) for e in events]
        if attendances:
            return round(min(100.0, max(attendances) / 500.0), 1)
        return min(100.0, len(events) * 15.0)

    def compute_pressure(self, inputs: PricingInputs) -> float:
        """Composite pricing pressure in [-1, +1]."""
        w_d = settings.PRICING_WEIGHT_DEMAND
        w_e = settings.PRICING_WEIGHT_EVENT
        w_w = settings.PRICING_WEIGHT_WEATHER
        w_i = settings.PRICING_WEIGHT_INVENTORY

        def norm(score: float) -> float:
            return (score - 50.0) / 50.0

        pressure = (
            w_d * norm(inputs.demand_score)
            + w_e * norm(inputs.event_score)
            + w_w * norm(inputs.weather_score)
            + w_i * norm(inputs.inventory_score)
        )
        # Business rules: convert rule boost % to pressure bump
        pressure += (inputs.business_rule_boost_pct / 100.0) * 0.5
        return max(-1.0, min(1.0, round(pressure, 4)))

    def evaluate_product(
        self,
        product: Product,
        inputs: PricingInputs,
        *,
        now: datetime | None = None,
        happy_hour_config: dict[str, Any] | None = None,
        weather_condition: str | None = None,
    ) -> ProductPricingDecision:
        now = now or datetime.now(timezone.utc)
        pressure = self.compute_pressure(inputs)

        raw_discount = 0.0
        raw_increase = 0.0
        action = PricingActionType.HOLD

        scale = settings.PRICING_ADJUSTMENT_SCALE
        if pressure <= self.PRESSURE_DISCOUNT_THRESHOLD:
            raw_discount = min(
                self.constraints.max_discount_pct,
                abs(pressure) * scale * self.constraints.max_discount_pct,
            )
            action = PricingActionType.DISCOUNT
        elif pressure >= self.PRESSURE_INCREASE_THRESHOLD:
            raw_increase = min(
                self.constraints.max_increase_pct,
                pressure * scale * self.constraints.max_increase_pct,
            )
            action = PricingActionType.PRICE_INCREASE

        floor = product.min_price
        ceiling = product.max_price
        constraints_notes: list[str] = []

        if raw_discount > 0:
            discount_pct, recommended, notes = self.constraints.apply_discount_cap(
                product.base_price,
                product.cost_price,
                raw_discount,
                min_price_floor=floor,
                max_price_ceiling=ceiling,
            )
            constraints_notes.extend(notes)
            increase_pct = 0.0
        elif raw_increase > 0:
            increase_pct, recommended, notes = self.constraints.apply_increase_cap(
                product.base_price,
                raw_increase,
                max_price_ceiling=ceiling,
            )
            discount_pct = 0.0
            constraints_notes.extend(notes)
            # Still respect margin floor (increase shouldn't violate)
            min_p = self.constraints.min_price_for_margin(product.cost_price)
            if floor is not None:
                min_p = max(min_p, floor)
            recommended = max(recommended, min_p)
        else:
            discount_pct = 0.0
            increase_pct = 0.0
            recommended = round(product.current_price, 2)

        margin_pct = self.constraints.margin_at_price(recommended, product.cost_price)

        bundle = self.offers.maybe_bundle(
            product_name=product.name,
            category=product.category,
            inputs=inputs,
            discount_pct=discount_pct,
            weather_condition=weather_condition,
        )
        if bundle:
            action = PricingActionType.BUNDLE if action == PricingActionType.HOLD else action

        hh_cfg = happy_hour_config or {}
        happy_hour = self.offers.maybe_happy_hour(
            inputs=inputs,
            discount_pct=discount_pct,
            now=now,
            hour_start=hh_cfg.get("hour_start"),
            hour_end=hh_cfg.get("hour_end"),
            days_of_week=hh_cfg.get("days_of_week"),
        )
        if happy_hour:
            if action in (PricingActionType.HOLD, PricingActionType.DISCOUNT):
                action = PricingActionType.HAPPY_HOUR

        explanations = self.explainer.build_steps(
            inputs,
            pressure,
            raw_discount,
            raw_increase,
            constraints_notes,
            inputs.business_rules_matched,
        )

        summary = self._build_summary(
            product, pressure, discount_pct, increase_pct, margin_pct, action
        )

        return ProductPricingDecision(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            category=product.category,
            base_price=product.base_price,
            current_price=product.current_price,
            recommended_price=recommended,
            cost_price=product.cost_price,
            discount_pct=discount_pct,
            price_increase_pct=increase_pct,
            bundle_offer=bundle,
            happy_hour=happy_hour,
            action_type=action,
            pricing_pressure=pressure,
            margin_pct=margin_pct,
            margin_floor_pct=self.constraints.min_margin_pct,
            constraints_applied=constraints_notes,
            explanations=explanations,
            summary=summary,
        )

    @staticmethod
    def _build_summary(
        product: Product,
        pressure: float,
        discount: float,
        increase: float,
        margin: float,
        action: PricingActionType,
    ) -> str:
        if action == PricingActionType.DISCOUNT:
            return (
                f"{product.name}: apply {discount:.1f}% discount "
                f"(pressure {pressure:+.2f}, margin {margin:.1f}%)"
            )
        if action == PricingActionType.PRICE_INCREASE:
            return (
                f"{product.name}: increase {increase:.1f}% "
                f"(pressure {pressure:+.2f}, margin {margin:.1f}%)"
            )
        if action == PricingActionType.BUNDLE:
            return f"{product.name}: bundle offer recommended (pressure {pressure:+.2f})"
        if action == PricingActionType.HAPPY_HOUR:
            return f"{product.name}: happy hour campaign (pressure {pressure:+.2f})"
        return f"{product.name}: hold price (pressure {pressure:+.2f})"


def business_rules_adjustment(
    product: Product,
    rules: list[PricingRule],
    *,
    weather: dict[str, Any] | None,
    events: list[dict[str, Any]],
    stock_qty: int,
    now: datetime,
) -> tuple[float, list[str]]:
    """
    Evaluate tenant business rules; return net % boost and matched rule names.
    Reuses legacy PricingEngine condition checks.
    """
    from backend.services.pricing_engine import PricingEngine

    matched: list[str] = []
    net_pct = 0.0

    for rule in rules:
        if not rule.is_active:
            continue
        target_category = rule.conditions.get("category")
        target_product_id = rule.conditions.get("product_id")
        if target_product_id and str(target_product_id) != str(product.id):
            continue
        if target_category and product.category != target_category:
            continue

        applies = False
        if rule.rule_type == "weather" and weather:
            applies = PricingEngine._check_weather_rule(rule.conditions, weather)
        elif rule.rule_type == "event" and events:
            applies = PricingEngine._check_event_rule(rule.conditions, events)
        elif rule.rule_type == "inventory":
            applies = PricingEngine._check_inventory_rule(rule.conditions, stock_qty)
        elif rule.rule_type == "time_of_day":
            applies = PricingEngine._check_time_rule(rule.conditions, now)

        if applies:
            matched.append(rule.name)
            if rule.adjustment_type == "percentage":
                net_pct += rule.adjustment_value
            elif rule.adjustment_type == "fixed" and product.base_price > 0:
                net_pct += (rule.adjustment_value / product.base_price) * 100.0

    return round(net_pct, 2), matched
