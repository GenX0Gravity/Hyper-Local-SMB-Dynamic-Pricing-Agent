"""Node 2: Predict demand from aggregated signals."""

from __future__ import annotations

import logging
from uuid import UUID

from backend.agent.state import (
    AgentPhase,
    DemandForecast,
    PricingAgentState,
    SignalBundle,
)

logger = logging.getLogger(__name__)


def _weather_factor(weather: dict | None) -> tuple[float, list[str]]:
    if not weather:
        return 1.0, []
    drivers = []
    factor = 1.0
    condition = (weather.get("condition") or "").lower()
    temp = weather.get("temp", 20)

    if condition in ("rain", "rainy", "drizzle"):
        factor *= 0.85
        drivers.append("rain_reduces_footfall")
    elif condition in ("clear", "sunny"):
        factor *= 1.08
        drivers.append("good_weather_boost")
    if temp > 32:
        factor *= 1.12
        drivers.append("heatwave_beverage_demand")
    elif temp < 5:
        factor *= 0.9
        drivers.append("cold_weather_slowdown")
    return factor, drivers


def _footfall_factor(footfall: dict | None) -> tuple[float, list[str]]:
    if not footfall:
        return 1.0, []
    idx = footfall.get("visitor_index", 1.0)
    busy = footfall.get("busy_percent", 50)
    factor = min(1.5, max(0.6, idx))
    drivers = []
    if busy >= 70:
        drivers.append("peak_popular_times")
    elif busy <= 30:
        drivers.append("low_traffic_period")
    return factor, drivers


def _event_factor(events: list) -> tuple[float, list[str]]:
    if not events:
        return 1.0, []
    max_att = max((e.get("attendance", 0) for e in events), default=0)
    if max_att >= 5000:
        return 1.25, ["major_local_event"]
    if max_att >= 1000:
        return 1.12, ["moderate_local_event"]
    return 1.05, ["minor_local_event"]


def _news_factor(news: list) -> tuple[float, list[str]]:
    if not news:
        return 1.0, []
    pos = sum(1 for n in news if n.get("sentiment_hint") == "positive")
    neg = sum(1 for n in news if n.get("sentiment_hint") == "negative")
    if pos > neg:
        return 1.05, ["positive_local_news"]
    if neg > pos:
        return 0.92, ["negative_local_news"]
    return 1.0, []


def predict_demand_node(state: PricingAgentState) -> dict:
    logger.info("Agent[%s]: predicting demand", state.get("run_id"))
    signals: SignalBundle = state.get("signals") or SignalBundle()
    location_id = state["location_id"]
    catalog = state.get("product_catalog") or []

    w_f, w_d = _weather_factor(signals.weather)
    f_f, f_d = _footfall_factor(signals.footfall)
    e_f, e_d = _event_factor(signals.events)
    n_f, n_d = _news_factor(signals.news)

    base_index = w_f * f_f * e_f * n_f
    drivers = w_d + f_d + e_d + n_d

    sales = signals.sales_summary or {}
    per_product = {p["product_id"]: p for p in sales.get("per_product", [])}

    forecasts: list[DemandForecast] = []

    if catalog:
        for p in catalog:
            pid = UUID(str(p["id"]))
            units = per_product.get(str(pid), {}).get("units_sold", 0)
            product_factor = 1.0
            if units == 0:
                product_factor = 0.85
                drivers_p = drivers + ["no_recent_sales"]
            elif units > 50:
                product_factor = 1.1
                drivers_p = drivers + ["strong_sales_history"]
            else:
                drivers_p = list(drivers)

            forecasts.append(
                DemandForecast(
                    location_id=location_id,
                    product_id=pid,
                    demand_index=round(min(2.0, base_index * product_factor), 3),
                    confidence=0.65 if signals.sources_ok else 0.45,
                    drivers=drivers_p,
                )
            )
    else:
        forecasts.append(
            DemandForecast(
                location_id=location_id,
                demand_index=round(min(2.0, base_index), 3),
                confidence=0.6,
                drivers=drivers,
            )
        )

    return {"phase": AgentPhase.PREDICT_DEMAND, "forecasts": forecasts}
