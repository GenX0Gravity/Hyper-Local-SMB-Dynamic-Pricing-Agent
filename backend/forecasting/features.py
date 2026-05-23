"""
Feature engineering for demand forecasting.

Inputs encoded:
  - Historical sales (lags, rolling stats)
  - Weather (temp, humidity, wind, condition)
  - Footfall (busy %, visitor index)
  - Local events (count, max attendance, impact)
  - Time of day / day of week (raw + cyclical)
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# Canonical feature column order used by trainer and predictor
FEATURE_COLUMNS: list[str] = [
    "hour_of_day",
    "day_of_week",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_weekend",
    "temperature_c",
    "humidity_pct",
    "wind_speed",
    "weather_rain",
    "weather_clear",
    "weather_cloud",
    "footfall_busy_pct",
    "footfall_visitor_index",
    "event_count",
    "event_max_attendance",
    "event_impact_score",
    "sales_lag_1h",
    "sales_lag_24h",
    "sales_rolling_7d_mean",
    "sales_rolling_7d_std",
]

TARGET_COLUMN = "demand_units"
SCORE_TARGET_COLUMN = "demand_score"


def _cyclical(value: float, period: float) -> tuple[float, float]:
    angle = 2 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def encode_weather(weather: dict[str, Any] | None) -> dict[str, float]:
    if not weather:
        return {
            "temperature_c": 20.0,
            "humidity_pct": 60.0,
            "wind_speed": 10.0,
            "weather_rain": 0.0,
            "weather_clear": 0.0,
            "weather_cloud": 1.0,
        }
    condition = str(weather.get("condition") or weather.get("condition_label") or "").lower()
    temp = float(weather.get("temp") or weather.get("temperature_c") or 20.0)
    humidity = float(weather.get("humidity") or weather.get("humidity_pct") or 60.0)
    wind = float(weather.get("wind_speed") or weather.get("wind_speed_ms") or 10.0)
    rain = 1.0 if any(x in condition for x in ("rain", "drizzle", "storm")) else 0.0
    clear = 1.0 if any(x in condition for x in ("clear", "sunny")) else 0.0
    cloud = 1.0 if not rain and not clear else 0.0
    return {
        "temperature_c": temp,
        "humidity_pct": humidity,
        "wind_speed": wind,
        "weather_rain": rain,
        "weather_clear": clear,
        "weather_cloud": cloud,
    }


def encode_footfall(footfall: dict[str, Any] | None) -> dict[str, float]:
    if not footfall:
        return {"footfall_busy_pct": 50.0, "footfall_visitor_index": 1.0}
    return {
        "footfall_busy_pct": float(footfall.get("busy_percent", 50.0)),
        "footfall_visitor_index": float(footfall.get("visitor_index", 1.0)),
    }


def encode_events(events: list[dict[str, Any]] | None) -> dict[str, float]:
    if not events:
        return {
            "event_count": 0.0,
            "event_max_attendance": 0.0,
            "event_impact_score": 0.0,
        }
    attendances = [float(e.get("attendance") or e.get("attendance_est") or 0) for e in events]
    impacts = [float(e.get("impact_score") or 0) for e in events]
    max_att = max(attendances) if attendances else 0.0
    impact = max(impacts) if impacts else min(1.0, max_att / 10000.0)
    return {
        "event_count": float(len(events)),
        "event_max_attendance": max_att,
        "event_impact_score": impact,
    }


def build_time_features(ts: pd.Timestamp) -> dict[str, float]:
    hour = int(ts.hour)
    dow = int(ts.dayofweek)
    hour_sin, hour_cos = _cyclical(hour, 24)
    dow_sin, dow_cos = _cyclical(dow, 7)
    return {
        "hour_of_day": float(hour),
        "day_of_week": float(dow),
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "dow_sin": dow_sin,
        "dow_cos": dow_cos,
        "is_weekend": 1.0 if dow >= 5 else 0.0,
    }


def row_to_features(
    ts: pd.Timestamp,
    weather: dict[str, Any] | None,
    footfall: dict[str, Any] | None,
    events: list[dict[str, Any]] | None,
    sales_lag_1h: float = 0.0,
    sales_lag_24h: float = 0.0,
    sales_rolling_7d_mean: float = 0.0,
    sales_rolling_7d_std: float = 0.0,
) -> dict[str, float]:
    features: dict[str, float] = {}
    features.update(build_time_features(ts))
    features.update(encode_weather(weather))
    features.update(encode_footfall(footfall))
    features.update(encode_events(events))
    features.update(
        {
            "sales_lag_1h": sales_lag_1h,
            "sales_lag_24h": sales_lag_24h,
            "sales_rolling_7d_mean": sales_rolling_7d_mean,
            "sales_rolling_7d_std": sales_rolling_7d_std,
        }
    )
    return features


def features_to_vector(features: dict[str, float]) -> np.ndarray:
    return np.array([features.get(col, 0.0) for col in FEATURE_COLUMNS], dtype=np.float32)


def dataframe_to_xy(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    x = df[FEATURE_COLUMNS].astype(np.float32).values
    y = df[TARGET_COLUMN].astype(np.float32).values
    return x, y


def units_to_demand_score(
    units: float | np.ndarray,
    scale_min: float,
    scale_max: float,
) -> float | np.ndarray:
    """Map predicted units to 0–100 demand score using training percentiles."""
    span = max(scale_max - scale_min, 1e-6)
    if isinstance(units, np.ndarray):
        return np.clip((units - scale_min) / span * 100.0, 0.0, 100.0)
    return float(np.clip((units - scale_min) / span * 100.0, 0.0, 100.0))
