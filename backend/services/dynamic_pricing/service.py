"""Dynamic Pricing Service — gathers signals and runs the pricing algorithm."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select

from backend.core.config import settings
from backend.models.product import Product
from backend.models.recommendation import Recommendation
from backend.models.rule import PricingRule
from backend.models.tenant import Tenant
from backend.services.dynamic_pricing.algorithm import (
    DynamicPricingAlgorithm,
    business_rules_adjustment,
)
from backend.services.dynamic_pricing.schemas import DynamicPricingReport, PricingInputs
from backend.services.event_intelligence.service import event_intelligence_service
from backend.services.weather_intelligence.service import weather_intelligence_service

logger = logging.getLogger(__name__)


class DynamicPricingService:
    def __init__(self, algorithm: DynamicPricingAlgorithm | None = None):
        self.algorithm = algorithm or DynamicPricingAlgorithm()

    async def evaluate_tenant(
        self,
        session: Session,
        tenant_id: UUID,
        *,
        demand_score: float | None = None,
        persist: bool = True,
        use_cache: bool = True,
    ) -> DynamicPricingReport:
        tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        weather_report = await weather_intelligence_service.get_intelligence_for_tenant(
            session, tenant_id, use_cache=use_cache, persist_signal=False
        )
        event_report = await event_intelligence_service.get_intelligence_for_tenant(
            session, tenant_id, use_cache=use_cache, persist_signal=False
        )

        weather_dict = weather_intelligence_service.to_legacy_weather_dict(weather_report)
        weather_dict["weather_score"] = self._weather_report_score(weather_report)
        events = event_intelligence_service.to_legacy_event_list(event_report)
        event_score = event_report.aggregate_impact_score

        if demand_score is None:
            demand_score = await self._estimate_demand_score(
                session, tenant_id, weather_dict, events
            )

        products = session.exec(
            select(Product).where(Product.tenant_id == tenant_id)
        ).all()
        rules = session.exec(
            select(PricingRule).where(
                PricingRule.tenant_id == tenant_id,
                PricingRule.is_active == True,
            )
        ).all()

        now = datetime.now(timezone.utc)
        happy_hour_cfg = self._happy_hour_from_rules(rules)

        decisions = []
        for product in products:
            inv_score = self.algorithm.inventory_score(product.stock_qty)
            rule_boost, matched = business_rules_adjustment(
                product,
                rules,
                weather=weather_dict,
                events=events,
                stock_qty=product.stock_qty,
                now=now,
            )
            inputs = PricingInputs(
                demand_score=demand_score,
                inventory_level=product.stock_qty,
                inventory_score=inv_score,
                event_score=event_score,
                weather_score=weather_dict.get("weather_score", 50.0),
                business_rule_boost_pct=rule_boost,
                business_rules_matched=matched,
            )
            decision = self.algorithm.evaluate_product(
                product,
                inputs,
                now=now,
                happy_hour_config=happy_hour_cfg,
                weather_condition=weather_dict.get("condition"),
            )
            decisions.append(decision)

        report = DynamicPricingReport(
            tenant_id=tenant_id,
            generated_at=now,
            inputs_snapshot={
                "demand_score": demand_score,
                "event_score": event_score,
                "weather_score": weather_dict.get("weather_score"),
                "product_count": len(products),
            },
            decisions=decisions,
            catalog_summary=self._summarize(decisions),
        )

        if persist:
            self._persist_recommendations(session, tenant_id, decisions, rules)

        return report

    async def _estimate_demand_score(
        self,
        session: Session,
        tenant_id: UUID,
        weather: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> float:
        """Use forecast model when available; else heuristic from signals."""
        try:
            from backend.forecasting.service import demand_forecasting_service
            from backend.forecasting.schemas import PredictRequest

            pred = await demand_forecasting_service.predict(
                session, tenant_id, PredictRequest(weather=weather, events=events)
            )
            return pred.demand_score
        except Exception:
            w = self.algorithm.weather_score_from_signal(weather)
            e = self.algorithm.event_score_from_signals(events)
            return round(min(100.0, max(0.0, 0.5 * w + 0.3 * e + 0.2 * 50.0)), 1)

    @staticmethod
    def _weather_report_score(report) -> float:
        score = 50.0
        c = report.current
        if c.is_heavy_rain:
            score += 25.0
        elif c.is_raining:
            score += 15.0
        if c.temperature_c >= 32:
            score += 10.0
        for adj in report.demand_adjustments:
            score += adj.delta_pct * 0.15
        return round(min(100.0, max(0.0, score)), 1)

    @staticmethod
    def _happy_hour_from_rules(rules: list[PricingRule]) -> dict[str, Any]:
        for rule in rules:
            if rule.rule_type == "time_of_day" and rule.is_active:
                return {
                    "hour_start": rule.conditions.get("hour_start", 14),
                    "hour_end": rule.conditions.get("hour_end", 16),
                    "days_of_week": rule.conditions.get("days_of_week", [0, 1, 2, 3, 4]),
                }
        return {}

    @staticmethod
    def _summarize(decisions: list) -> dict[str, Any]:
        discounts = [d for d in decisions if d.discount_pct > 0]
        increases = [d for d in decisions if d.price_increase_pct > 0]
        bundles = [d for d in decisions if d.bundle_offer]
        happy_hours = [d for d in decisions if d.happy_hour]
        return {
            "total_products": len(decisions),
            "discount_count": len(discounts),
            "increase_count": len(increases),
            "bundle_count": len(bundles),
            "happy_hour_count": len(happy_hours),
            "avg_discount_pct": round(
                sum(d.discount_pct for d in discounts) / len(discounts), 2
            )
            if discounts
            else 0.0,
            "avg_increase_pct": round(
                sum(d.price_increase_pct for d in increases) / len(increases), 2
            )
            if increases
            else 0.0,
        }

    def _persist_recommendations(
        self,
        session: Session,
        tenant_id: UUID,
        decisions: list,
        rules: list[PricingRule],
    ) -> None:
        now = datetime.now(timezone.utc)
        default_rule_id = rules[0].id if rules else None

        for decision in decisions:
            if round(decision.recommended_price, 2) == round(decision.current_price, 2):
                if not decision.bundle_offer and not decision.happy_hour:
                    continue

            reason = self._format_reason(decision)
            existing = session.exec(
                select(Recommendation).where(
                    Recommendation.product_id == decision.product_id,
                    Recommendation.status == "pending",
                )
            ).first()

            if existing:
                existing.recommended_price = decision.recommended_price
                existing.reason = reason
                existing.expires_at = now + timedelta(hours=settings.PRICING_RECOMMENDATION_TTL_HOURS)
                session.add(existing)
            else:
                session.add(
                    Recommendation(
                        tenant_id=tenant_id,
                        product_id=decision.product_id,
                        rule_id=default_rule_id,
                        recommended_price=decision.recommended_price,
                        previous_price=decision.current_price,
                        reason=reason,
                        status="pending",
                        expires_at=now
                        + timedelta(hours=settings.PRICING_RECOMMENDATION_TTL_HOURS),
                    )
                )

        session.commit()

    @staticmethod
    def _format_reason(decision) -> str:
        lines = [decision.summary, ""]
        if decision.discount_pct > 0:
            lines.append(f"Discount: {decision.discount_pct:.1f}%")
        if decision.price_increase_pct > 0:
            lines.append(f"Price increase: {decision.price_increase_pct:.1f}%")
        if decision.bundle_offer:
            b = decision.bundle_offer
            lines.append(f"Bundle: {b.title} ({b.discount_pct:.0f}% off, {b.valid_hours}h)")
        if decision.happy_hour:
            h = decision.happy_hour
            lines.append(
                f"Happy Hour: {h.title} ({h.discount_pct:.0f}% off, "
                f"{h.hour_start}:00–{h.hour_end}:00)"
            )
        lines.append("")
        lines.append("Explanation:")
        for step in decision.explanations:
            lines.append(f"  • [{step.factor}] {step.detail}")
        if decision.constraints_applied:
            lines.append("")
            lines.append("Constraints:")
            for c in decision.constraints_applied:
                lines.append(f"  • {c}")
        return "\n".join(lines)


dynamic_pricing_service = DynamicPricingService()
