"""Tests for Weather Intelligence Service."""

import pytest
from datetime import datetime, timezone

from backend.services.weather_intelligence.rules import WeatherRulesEngine
from backend.services.weather_intelligence.schemas import (
    ForecastWindow,
    RainIntensity,
    WeatherCondition,
    WeatherForecast,
    WeatherSnapshot,
)
from backend.services.weather_intelligence.client import _rain_intensity, _parse_current


def test_heavy_rain_detection():
    data = {
        "main": {"temp": 15, "feels_like": 14, "humidity": 90},
        "wind": {"speed": 6},
        "weather": [{"main": "Rain", "description": "heavy rain"}],
        "rain": {"1h": 8.5},
    }
    snap = _parse_current(data, "test")
    assert snap.is_heavy_rain is True
    assert snap.rain_intensity == RainIntensity.HEAVY


def test_rules_engine_heavy_rain_boosts():
    current = WeatherSnapshot(
        temperature_c=16,
        feels_like_c=14,
        humidity_pct=88,
        wind_speed_ms=7,
        condition=WeatherCondition.RAIN,
        condition_label="heavy rain",
        rain_intensity=RainIntensity.HEAVY,
        precipitation_mm_1h=9.0,
        is_raining=True,
        is_heavy_rain=True,
        recorded_at=datetime.now(timezone.utc),
    )
    forecast = WeatherForecast(
        location_key="0,0",
        windows=[],
        heavy_rain_within_hours=6,
    )
    report = WeatherRulesEngine().evaluate(
        current, forecast, business_type="cafe", tenant_id="test"
    )
    metrics = {a.metric: a for a in report.demand_adjustments}
    assert "chai_demand_score" in metrics
    assert metrics["chai_demand_score"].delta_pct > 0
    assert "indoor_seating_demand_score" in metrics
    assert len(report.offers) >= 3
    assert any(a.code == "heavy_rain" for a in report.alerts)


def test_rules_no_rain_minimal_offers():
    current = WeatherSnapshot(
        temperature_c=25,
        feels_like_c=26,
        humidity_pct=50,
        wind_speed_ms=3,
        condition=WeatherCondition.CLEAR,
        condition_label="clear",
        rain_intensity=RainIntensity.NONE,
        is_raining=False,
        is_heavy_rain=False,
        recorded_at=datetime.now(timezone.utc),
    )
    report = WeatherRulesEngine().evaluate(current, None, business_type="cafe")
    assert "heavy_rain_demand_boost" not in report.rules_fired
