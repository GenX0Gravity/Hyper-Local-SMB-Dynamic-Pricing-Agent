"""Human-readable explanations for every pricing recommendation."""

from __future__ import annotations

from backend.services.dynamic_pricing.schemas import (
    ExplanationStep,
    PricingInputs,
    ProductPricingDecision,
)


class ExplanationBuilder:
    def build_steps(
        self,
        inputs: PricingInputs,
        pricing_pressure: float,
        raw_discount: float,
        raw_increase: float,
        constraints: list[str],
        rules_matched: list[str],
    ) -> list[ExplanationStep]:
        steps: list[ExplanationStep] = []

        demand_delta = inputs.demand_score - 50.0
        steps.append(
            ExplanationStep(
                factor="demand_score",
                value=round(inputs.demand_score, 1),
                impact="increase" if demand_delta > 5 else ("decrease" if demand_delta < -5 else "neutral"),
                detail=(
                    f"Demand index {inputs.demand_score:.0f}/100 "
                    f"({'above' if demand_delta > 0 else 'below'} neutral 50)"
                ),
            )
        )

        steps.append(
            ExplanationStep(
                factor="inventory",
                value=inputs.inventory_level,
                impact="increase" if inputs.inventory_score >= 60 else ("decrease" if inputs.inventory_score <= 40 else "neutral"),
                detail=(
                    f"Stock {inputs.inventory_level} units "
                    f"(scarcity score {inputs.inventory_score:.0f}/100)"
                ),
            )
        )

        if inputs.event_score > 10:
            steps.append(
                ExplanationStep(
                    factor="event_score",
                    value=round(inputs.event_score, 1),
                    impact="increase" if inputs.event_score >= 55 else "neutral",
                    detail=f"Local event impact {inputs.event_score:.0f}/100",
                )
            )

        steps.append(
            ExplanationStep(
                factor="weather_score",
                value=round(inputs.weather_score, 1),
                impact="increase" if inputs.weather_score >= 60 else ("decrease" if inputs.weather_score <= 40 else "neutral"),
                detail=f"Weather-driven demand score {inputs.weather_score:.0f}/100",
            )
        )

        if rules_matched:
            steps.append(
                ExplanationStep(
                    factor="business_rules",
                    value=inputs.business_rule_boost_pct,
                    impact="increase" if inputs.business_rule_boost_pct > 0 else "decrease",
                    detail=f"Matched rules: {', '.join(rules_matched)}",
                )
            )

        steps.append(
            ExplanationStep(
                factor="pricing_pressure",
                value=round(pricing_pressure, 3),
                impact="increase" if pricing_pressure > 0.1 else ("decrease" if pricing_pressure < -0.1 else "neutral"),
                detail=f"Composite pressure {pricing_pressure:+.2f} (−1 discount … +1 surge)",
            )
        )

        if raw_discount > 0:
            steps.append(
                ExplanationStep(
                    factor="discount_signal",
                    value=raw_discount,
                    impact="decrease",
                    detail=f"Algorithm proposed {raw_discount:.1f}% discount before constraints",
                )
            )
        if raw_increase > 0:
            steps.append(
                ExplanationStep(
                    factor="increase_signal",
                    value=raw_increase,
                    impact="increase",
                    detail=f"Algorithm proposed {raw_increase:.1f}% price increase before constraints",
                )
            )

        for note in constraints:
            steps.append(
                ExplanationStep(
                    factor="constraint",
                    value=note,
                    impact="neutral",
                    detail=note,
                )
            )

        return steps

    def summarize(self, decision: ProductPricingDecision) -> str:
        parts = [decision.summary] if decision.summary else []
        if decision.discount_pct > 0:
            parts.append(f"Discount {decision.discount_pct:.1f}%")
        if decision.price_increase_pct > 0:
            parts.append(f"Increase {decision.price_increase_pct:.1f}%")
        if decision.bundle_offer:
            parts.append(f"Bundle: {decision.bundle_offer.title}")
        if decision.happy_hour:
            parts.append(f"Happy Hour: {decision.happy_hour.title}")
        parts.append(f"→ ${decision.recommended_price:.2f} (margin {decision.margin_pct:.1f}%)")
        return " | ".join(parts)
