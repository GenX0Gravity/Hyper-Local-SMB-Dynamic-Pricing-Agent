"""Pydantic schemas for weather intelligence."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RainIntensity(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    CLOUDS = "clouds"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    MIST = "mist"
    EXTREME = "extreme"


class WeatherSnapshot(BaseModel):
    """Normalized current conditions from OpenWeatherMap."""

    temperature_c: float
    feels_like_c: float
    humidity_pct: float
    wind_speed_ms: float
    wind_gust_ms: Optional[float] = None
    condition: WeatherCondition
    condition_label: str
    rain_intensity: RainIntensity
    precipitation_mm_1h: float = 0.0
    is_raining: bool = False
    is_heavy_rain: bool = False
    recorded_at: datetime
    source: str = "OpenWeatherMap"
    raw: dict[str, Any] = Field(default_factory=dict)


class ForecastWindow(BaseModel):
    """Single 3-hour forecast bucket."""

    starts_at: datetime
    temperature_c: float
    humidity_pct: float
    wind_speed_ms: float
    pop: float = Field(description="Probability of precipitation 0-1")
    rain_mm: float = 0.0
    condition: WeatherCondition
    is_heavy_rain_predicted: bool = False


class WeatherForecast(BaseModel):
    location_key: str
    windows: list[ForecastWindow] = Field(default_factory=list)
    heavy_rain_within_hours: Optional[int] = None
    source: str = "OpenWeatherMap"


class DemandAdjustment(BaseModel):
    metric: str
    baseline_score: float = 50.0
    adjusted_score: float
    delta_pct: float
    reason: str


class WeatherOffer(BaseModel):
    offer_id: str
    title: str
    description: str
    category: str
    adjustment_type: str  # percentage | fixed | bundle
    adjustment_value: float
    valid_hours: int = 6
    trigger: str


class WeatherAlert(BaseModel):
    severity: str  # info | warning | critical
    code: str
    message: str


class WeatherIntelligenceReport(BaseModel):
    tenant_id: Optional[str] = None
    location: dict[str, float]
    current: WeatherSnapshot
    forecast: Optional[WeatherForecast] = None
    alerts: list[WeatherAlert] = Field(default_factory=list)
    demand_adjustments: list[DemandAdjustment] = Field(default_factory=list)
    offers: list[WeatherOffer] = Field(default_factory=list)
    rules_fired: list[str] = Field(default_factory=list)
    generated_at: datetime
    cache_hit: bool = False
