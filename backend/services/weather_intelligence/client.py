"""OpenWeatherMap API client — current weather and 5-day/3-hour forecast."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.core.config import settings
from backend.services.weather_intelligence.schemas import (
    ForecastWindow,
    RainIntensity,
    WeatherCondition,
    WeatherForecast,
    WeatherSnapshot,
)

logger = logging.getLogger(__name__)

OWM_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"


def _map_condition(main: str) -> WeatherCondition:
    key = (main or "").lower()
    mapping = {
        "clear": WeatherCondition.CLEAR,
        "clouds": WeatherCondition.CLOUDS,
        "rain": WeatherCondition.RAIN,
        "drizzle": WeatherCondition.DRIZZLE,
        "thunderstorm": WeatherCondition.THUNDERSTORM,
        "snow": WeatherCondition.SNOW,
        "mist": WeatherCondition.MIST,
        "fog": WeatherCondition.MIST,
        "haze": WeatherCondition.MIST,
    }
    return mapping.get(key, WeatherCondition.CLOUDS)


def _rain_intensity(mm_1h: float, condition: WeatherCondition, pop: float = 0.0) -> RainIntensity:
    if condition not in (
        WeatherCondition.RAIN,
        WeatherCondition.DRIZZLE,
        WeatherCondition.THUNDERSTORM,
    ) and mm_1h < 0.1:
        if pop < 0.4:
            return RainIntensity.NONE
    if mm_1h >= settings.WEATHER_HEAVY_RAIN_MM_1H:
        return RainIntensity.HEAVY
    if mm_1h >= 2.0 or pop >= 0.7:
        return RainIntensity.MODERATE
    if mm_1h > 0 or pop >= 0.35:
        return RainIntensity.LIGHT
    return RainIntensity.NONE


def _parse_current(data: dict[str, Any], source: str) -> WeatherSnapshot:
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather = (data.get("weather") or [{}])[0]
    rain = data.get("rain", {})
    mm_1h = float(rain.get("1h") or rain.get("3h", 0) or 0)
    condition = _map_condition(weather.get("main", ""))
    intensity = _rain_intensity(mm_1h, condition)
    is_raining = intensity != RainIntensity.NONE
    is_heavy = intensity == RainIntensity.HEAVY

    return WeatherSnapshot(
        temperature_c=float(main.get("temp", 20)),
        feels_like_c=float(main.get("feels_like", main.get("temp", 20))),
        humidity_pct=float(main.get("humidity", 60)),
        wind_speed_ms=float(wind.get("speed", 0)),
        wind_gust_ms=wind.get("gust"),
        condition=condition,
        condition_label=weather.get("description", ""),
        rain_intensity=intensity,
        precipitation_mm_1h=mm_1h,
        is_raining=is_raining,
        is_heavy_rain=is_heavy,
        recorded_at=datetime.now(timezone.utc),
        source=source,
        raw=data,
    )


class OpenWeatherMapClient:
    def __init__(self, api_key: str | None = None, cache=None):
        self.api_key = api_key or settings.OPENWEATHER_API_KEY
        self.cache = cache

    async def fetch_current(
        self, latitude: float, longitude: float, use_cache: bool = True
    ) -> WeatherSnapshot:
        if use_cache and self.cache:
            cached = self.cache.get_current(latitude, longitude)
            if cached:
                return WeatherSnapshot.model_validate(cached)

        if not self.api_key:
            snap = self._mock_current(latitude, longitude)
        else:
            snap = await self._api_current(latitude, longitude)

        if self.cache:
            self.cache.set_current(latitude, longitude, snap.model_dump(mode="json"))
        return snap

    async def fetch_forecast(
        self, latitude: float, longitude: float, use_cache: bool = True
    ) -> WeatherForecast:
        if use_cache and self.cache:
            cached = self.cache.get_forecast(latitude, longitude)
            if cached:
                return WeatherForecast.model_validate(cached)

        if not self.api_key:
            forecast = self._mock_forecast(latitude, longitude)
        else:
            forecast = await self._api_forecast(latitude, longitude)

        if self.cache:
            self.cache.set_forecast(
                latitude, longitude, forecast.model_dump(mode="json")
            )
        return forecast

    async def _api_current(self, lat: float, lon: float) -> WeatherSnapshot:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(OWM_CURRENT, params=params, timeout=12.0)
            if response.status_code != 200:
                logger.error("OpenWeather current failed: %s", response.text)
                return _parse_current({}, "API_Fallback")
            return _parse_current(response.json(), "OpenWeatherMap")

    async def _api_forecast(self, lat: float, lon: float) -> WeatherForecast:
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        windows: list[ForecastWindow] = []
        heavy_within: int | None = None

        async with httpx.AsyncClient() as client:
            response = await client.get(OWM_FORECAST, params=params, timeout=12.0)
            if response.status_code != 200:
                logger.error("OpenWeather forecast failed: %s", response.text)
                return WeatherForecast(
                    location_key=f"{lat:.4f},{lon:.4f}", windows=[], source="API_Fallback"
                )
            data = response.json()

        now = datetime.now(timezone.utc)
        for i, item in enumerate(data.get("list", [])[:8]):
            main = item.get("main", {})
            wind = item.get("wind", {})
            weather = (item.get("weather") or [{}])[0]
            rain = item.get("rain", {})
            mm = float(rain.get("3h", 0) or 0)
            pop = float(item.get("pop", 0))
            condition = _map_condition(weather.get("main", ""))
            heavy = (
                _rain_intensity(mm / 3.0, condition, pop) == RainIntensity.HEAVY
                or (pop >= 0.75 and condition in (WeatherCondition.RAIN, WeatherCondition.THUNDERSTORM))
            )
            starts = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            if heavy and heavy_within is None:
                heavy_within = max(0, int((starts - now).total_seconds() // 3600))

            windows.append(
                ForecastWindow(
                    starts_at=starts,
                    temperature_c=float(main.get("temp", 20)),
                    humidity_pct=float(main.get("humidity", 60)),
                    wind_speed_ms=float(wind.get("speed", 0)),
                    pop=pop,
                    rain_mm=mm,
                    condition=condition,
                    is_heavy_rain_predicted=heavy,
                )
            )

        return WeatherForecast(
            location_key=f"{lat:.4f},{lon:.4f}",
            windows=windows,
            heavy_rain_within_hours=heavy_within,
            source="OpenWeatherMap",
        )

    def _mock_current(self, lat: float, lon: float) -> WeatherSnapshot:
        random.seed(int(lat * 100 + lon * 100))
        scenario = random.choice(["sunny", "rainy", "heavy_rain", "cloudy"])
        random.seed(None)

        if scenario == "heavy_rain":
            data = {
                "main": {"temp": 16, "feels_like": 14, "humidity": 88},
                "wind": {"speed": 8.5},
                "weather": [{"main": "Rain", "description": "heavy intensity rain"}],
                "rain": {"1h": 9.2},
            }
        elif scenario == "rainy":
            data = {
                "main": {"temp": 18, "feels_like": 17, "humidity": 75},
                "wind": {"speed": 5.0},
                "weather": [{"main": "Rain", "description": "light rain"}],
                "rain": {"1h": 1.5},
            }
        else:
            data = {
                "main": {"temp": 24, "feels_like": 25, "humidity": 55},
                "wind": {"speed": 3.2},
                "weather": [{"main": "Clear", "description": "clear sky"}],
            }
        return _parse_current(data, "MockTelemetry")

    def _mock_forecast(self, lat: float, lon: float) -> WeatherForecast:
        now = datetime.now(timezone.utc)
        from datetime import timedelta

        windows = []
        heavy_within = None
        for i in range(8):
            starts = now + timedelta(hours=3 * (i + 1))
            heavy = i in (1, 2)
            if heavy and heavy_within is None:
                heavy_within = 3 * (i + 1)
            windows.append(
                ForecastWindow(
                    starts_at=starts,
                    temperature_c=17.0,
                    humidity_pct=85.0,
                    wind_speed_ms=7.0,
                    pop=0.85 if heavy else 0.2,
                    rain_mm=8.0 if heavy else 0.0,
                    condition=WeatherCondition.RAIN if heavy else WeatherCondition.CLOUDS,
                    is_heavy_rain_predicted=heavy,
                )
            )
        return WeatherForecast(
            location_key=f"{lat:.4f},{lon:.4f}",
            windows=windows,
            heavy_rain_within_hours=heavy_within,
            source="MockTelemetry",
        )
