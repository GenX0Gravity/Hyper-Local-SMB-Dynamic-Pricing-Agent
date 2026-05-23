"""Business rules engine — weather-driven demand and offers."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.core.config import settings
from backend.services.weather_intelligence.schemas import (
    DemandAdjustment,
    RainIntensity,
    WeatherAlert,
    WeatherForecast,
    WeatherIntelligenceReport,
    WeatherOffer,
    WeatherSnapshot,
)


class WeatherRulesEngine:
    """Evaluates monitored metrics and produces demand adjustments + offers."""

    def evaluate(
        self,
        current: WeatherSnapshot,
        forecast: WeatherForecast | None,
        business_type: str = "cafe",
        tenant_id: str | None = None,
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> WeatherIntelligenceReport:
        alerts: list[WeatherAlert] = []
        adjustments: list[DemandAdjustment] = []
        offers: list[WeatherOffer] = []
        fired: list[str] = []

        heavy_now = current.is_heavy_rain or current.rain_intensity == RainIntensity.HEAVY
        heavy_predicted = forecast and forecast.heavy_rain_within_hours is not None
        heavy_soon = heavy_predicted and (forecast.heavy_rain_within_hours or 99) <= 12

        if heavy_now or heavy_soon:
            fired.append("heavy_rain_demand_boost")
            self._apply_heavy_rain_rules(
                adjustments, offers, alerts, heavy_now, heavy_soon, forecast, business_type
            )

        if current.temperature_c >= settings.WEATHER_HEATWAVE_TEMP_C:
            fired.append("heatwave_cold_drink_boost")
            adjustments.append(
                DemandAdjustment(
                    metric="cold_beverage_demand_score",
                    adjusted_score=72.0,
                    delta_pct=18.0,
                    reason=f"Heat ({current.temperature_c:.0f}°C) lifts iced drink demand",
                )
            )

        if current.wind_speed_ms >= settings.WEATHER_HIGH_WIND_MS:
            fired.append("high_wind_alert")
            alerts.append(
                WeatherAlert(
                    severity="warning",
                    code="high_wind",
                    message=f"Wind {current.wind_speed_ms:.1f} m/s — secure outdoor seating",
                )
            )

        if current.humidity_pct >= 85 and current.is_raining:
            fired.append("humid_rain_comfort")
            offers.append(
                WeatherOffer(
                    offer_id="humid-comfort-warmth",
                    title="Warm & Dry Combo",
                    description="Pair any hot drink with pastry at 12% off.",
                    category="Beverages",
                    adjustment_type="percentage",
                    adjustment_value=-12.0,
                    valid_hours=4,
                    trigger="high_humidity_rain",
                )
            )

        return WeatherIntelligenceReport(
            tenant_id=tenant_id,
            location={"latitude": latitude, "longitude": longitude},
            current=current,
            forecast=forecast,
            alerts=alerts,
            demand_adjustments=adjustments,
            offers=offers,
            rules_fired=fired,
            generated_at=datetime.now(timezone.utc),
        )

    def _apply_heavy_rain_rules(
        self,
        adjustments: list[DemandAdjustment],
        offers: list[WeatherOffer],
        alerts: list[WeatherAlert],
        heavy_now: bool,
        heavy_soon: bool,
        forecast: WeatherForecast | None,
        business_type: str,
    ) -> None:
        hours_msg = ""
        if heavy_soon and forecast:
            hours_msg = f" in ~{forecast.heavy_rain_within_hours}h"

        alerts.append(
            WeatherAlert(
                severity="critical" if heavy_now else "warning",
                code="heavy_rain",
                message=(
                    "Heavy rain"
                    + (" now" if heavy_now else "")
                    + (hours_msg if heavy_soon else "")
                    + " — activating rain playbook"
                ),
            )
        )

        chai_boost = settings.WEATHER_CHAI_DEMAND_BOOST_PCT
        indoor_boost = settings.WEATHER_INDOOR_SEATING_BOOST_PCT

        adjustments.append(
            DemandAdjustment(
                metric="chai_demand_score",
                adjusted_score=min(100.0, 50.0 + chai_boost),
                delta_pct=chai_boost,
                reason="Heavy rain increases hot chai / tea demand",
            )
        )
        adjustments.append(
            DemandAdjustment(
                metric="indoor_seating_demand_score",
                adjusted_score=min(100.0, 50.0 + indoor_boost),
                delta_pct=indoor_boost,
                reason="Rain drives foot traffic indoors",
            )
        )

        offers.extend(
            [
                WeatherOffer(
                    offer_id="rainy-chai-combo",
                    title="Rainy Day Chai Special",
                    description="15% off masala chai & hot tea when it's pouring.",
                    category="Beverages",
                    adjustment_type="percentage",
                    adjustment_value=-15.0,
                    valid_hours=6,
                    trigger="heavy_rain",
                ),
                WeatherOffer(
                    offer_id="indoor-comfort-hour",
                    title="Indoor Comfort Hour",
                    description="Free upgrade to large hot drink with any food item.",
                    category="Beverages",
                    adjustment_type="bundle",
                    adjustment_value=0.0,
                    valid_hours=4,
                    trigger="heavy_rain_indoor",
                ),
                WeatherOffer(
                    offer_id="rainy-pastry-pair",
                    title="Cozy Pastry Pairing",
                    description="Buy one hot beverage, get 20% off pastries.",
                    category="Pastries",
                    adjustment_type="percentage",
                    adjustment_value=-20.0,
                    valid_hours=5,
                    trigger="heavy_rain",
                ),
            ]
        )

        if business_type in ("cafe", "restaurant", "retail"):
            offers.append(
                WeatherOffer(
                    offer_id="outdoor-to-indoor",
                    title="Skip the Rain — Dine In",
                    description="10% off entire bill for dine-in during heavy rain.",
                    category="Storewide",
                    adjustment_type="percentage",
                    adjustment_value=-10.0,
                    valid_hours=3,
                    trigger="heavy_rain_seating",
                )
            )
