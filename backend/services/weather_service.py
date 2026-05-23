"""
Legacy weather service — delegates to Weather Intelligence Service.
"""

import logging
from typing import Any

from backend.services.weather_intelligence.service import weather_intelligence_service

logger = logging.getLogger(__name__)


class WeatherService:
    @staticmethod
    async def get_current_weather(latitude: float, longitude: float) -> dict[str, Any]:
        report = await weather_intelligence_service.get_intelligence(
            latitude, longitude, use_cache=True
        )
        return weather_intelligence_service.to_legacy_weather_dict(report)


weather_service = WeatherService()
