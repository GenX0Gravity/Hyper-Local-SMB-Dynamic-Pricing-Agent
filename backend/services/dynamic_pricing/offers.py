"""Bundle offers and happy hour campaign generators."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.services.dynamic_pricing.schemas import (
    BundleOffer,
    HappyHourCampaign,
    PricingInputs,
)


class OfferGenerator:
    """Produces bundle and happy-hour outputs from signal context."""

    def maybe_bundle(
        self,
        *,
        product_name: str,
        category: str | None,
        inputs: PricingInputs,
        discount_pct: float,
        weather_condition: str | None = None,
        event_category: str | None = None,
    ) -> BundleOffer | None:
        cat = (category or "").lower()
        triggers: list[str] = []

        if inputs.weather_score >= 65 and discount_pct > 0:
            triggers.append("high_weather_demand")
        if inputs.event_score >= 55:
            triggers.append("local_event_footfall")
        if inputs.demand_score >= 60 and discount_pct == 0:
            triggers.append("high_demand_pairing")

        if not triggers:
            return None

        if "beverage" in cat or "coffee" in product_name.lower():
            if "high_weather_demand" in triggers or inputs.weather_score >= 70:
                return BundleOffer(
                    offer_id="rainy-comfort-bundle",
                    title="Rainy Day Comfort Bundle",
                    description="Hot drink + pastry at 15% off during wet weather.",
                    primary_category=category or "Beverages",
                    discount_pct=min(15.0, discount_pct + 5) if discount_pct else 15.0,
                    valid_hours=6,
                    trigger="weather_score_high",
                )
            if inputs.event_score >= 55:
                return BundleOffer(
                    offer_id="event-crowd-bundle",
                    title="Event Crowd Combo",
                    description="Pair any large beverage with a snack at 12% off.",
                    primary_category=category or "Beverages",
                    discount_pct=12.0,
                    valid_hours=4,
                    trigger="event_score_high",
                )

        if "pastry" in cat or "bakery" in cat:
            return BundleOffer(
                offer_id="pastry-pair-bundle",
                title="Pastry Pairing Deal",
                description="Buy any beverage, get 20% off pastries.",
                primary_category=category or "Pastries",
                discount_pct=20.0,
                valid_hours=5,
                trigger="+".join(triggers),
            )

        return BundleOffer(
            offer_id="storewide-signal-bundle",
            title="Smart Store Bundle",
            description="10% off when purchasing two or more items from featured categories.",
            primary_category=category or "Storewide",
            discount_pct=10.0,
            valid_hours=4,
            trigger="+".join(triggers),
        )

    def maybe_happy_hour(
        self,
        *,
        inputs: PricingInputs,
        discount_pct: float,
        now: datetime | None = None,
        hour_start: int | None = None,
        hour_end: int | None = None,
        days_of_week: list[int] | None = None,
    ) -> HappyHourCampaign | None:
        now = now or datetime.now(timezone.utc)
        start = hour_start if hour_start is not None else 14
        end = hour_end if hour_end is not None else 16
        days = days_of_week if days_of_week is not None else [0, 1, 2, 3, 4]

        in_window = start <= now.hour < end and now.weekday() in days
        low_demand = inputs.demand_score < 48

        if not (in_window or (low_demand and inputs.demand_score < 42)):
            return None

        hh_discount = max(discount_pct, 12.0) if discount_pct > 0 else 12.0
        return HappyHourCampaign(
            campaign_id="afternoon-happy-hour",
            title="Afternoon Happy Hour",
            description=f"${hh_discount:.0f}% off select items {start}:00–{end}:00.",
            discount_pct=round(min(hh_discount, 30.0), 1),
            hour_start=start,
            hour_end=end,
            days_of_week=days,
            trigger="low_demand_time_window" if low_demand else "scheduled_happy_hour",
        )
