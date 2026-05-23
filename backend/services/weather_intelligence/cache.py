"""Redis caching for weather API responses."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from backend.core.config import settings

logger = logging.getLogger(__name__)

CURRENT_KEY = "weather:current:{lat:.4f}:{lon:.4f}"
FORECAST_KEY = "weather:forecast:{lat:.4f}:{lon:.4f}"
INTELLIGENCE_KEY = "weather:intelligence:{tenant_id}"


class WeatherCache:
    def __init__(self, redis_url: str | None = None):
        self._redis: redis.Redis | None = None
        url = redis_url or settings.REDIS_CACHE_URL
        try:
            client = redis.from_url(url, decode_responses=True)
            client.ping()
            self._redis = client
        except Exception as exc:
            logger.warning("Weather cache unavailable (Redis): %s", exc)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self._redis:
            return None
        raw = self._redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    def set(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        if not self._redis:
            return
        self._redis.setex(key, ttl_seconds, json.dumps(payload, default=str))

    def get_current(self, lat: float, lon: float) -> Optional[dict[str, Any]]:
        return self.get(CURRENT_KEY.format(lat=lat, lon=lon))

    def set_current(self, lat: float, lon: float, payload: dict[str, Any]) -> None:
        self.set(
            CURRENT_KEY.format(lat=lat, lon=lon),
            payload,
            settings.WEATHER_CACHE_TTL_CURRENT,
        )

    def get_forecast(self, lat: float, lon: float) -> Optional[dict[str, Any]]:
        return self.get(FORECAST_KEY.format(lat=lat, lon=lon))

    def set_forecast(self, lat: float, lon: float, payload: dict[str, Any]) -> None:
        self.set(
            FORECAST_KEY.format(lat=lat, lon=lon),
            payload,
            settings.WEATHER_CACHE_TTL_FORECAST,
        )

    def get_intelligence(self, tenant_id: str) -> Optional[dict[str, Any]]:
        return self.get(INTELLIGENCE_KEY.format(tenant_id=tenant_id))

    def set_intelligence(self, tenant_id: str, payload: dict[str, Any]) -> None:
        self.set(
            INTELLIGENCE_KEY.format(tenant_id=tenant_id),
            payload,
            settings.WEATHER_CACHE_TTL_INTELLIGENCE,
        )

    def invalidate_location(self, lat: float, lon: float) -> None:
        if not self._redis:
            return
        self._redis.delete(
            CURRENT_KEY.format(lat=lat, lon=lon),
            FORECAST_KEY.format(lat=lat, lon=lon),
        )
