"""Weather Intelligence Service — orchestrates API, cache, and rules."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select

from backend.models.signal import DemandSignal
from backend.models.tenant import Tenant
from backend.services.weather_intelligence.cache import WeatherCache
from backend.services.weather_intelligence.client import OpenWeatherMapClient
from backend.services.weather_intelligence.rules import WeatherRulesEngine
from backend.services.weather_intelligence.schemas import WeatherIntelligenceReport

logger = logging.getLogger(__name__)


class WeatherIntelligenceService:
    def __init__(
        self,
        cache: WeatherCache | None = None,
        client: OpenWeatherMapClient | None = None,
        rules: WeatherRulesEngine | None = None,
    ):
        self.cache = cache or WeatherCache()
        self.client = client or OpenWeatherMapClient(cache=self.cache)
        self.rules = rules or WeatherRulesEngine()

    async def get_intelligence(
        self,
        latitude: float,
        longitude: float,
        business_type: str = "cafe",
        tenant_id: UUID | None = None,
        use_cache: bool = True,
    ) -> WeatherIntelligenceReport:
        tid = str(tenant_id) if tenant_id else None
        if use_cache and tid:
            cached = self.cache.get_intelligence(tid)
            if cached:
                report = WeatherIntelligenceReport.model_validate(cached)
                return report.model_copy(update={"cache_hit": True})

        current, forecast = await self._fetch_all(latitude, longitude, use_cache)
        report = self.rules.evaluate(
            current=current,
            forecast=forecast,
            business_type=business_type,
            tenant_id=tid,
            latitude=latitude,
            longitude=longitude,
        )

        if tid:
            self.cache.set_intelligence(tid, report.model_dump(mode="json"))
        return report

    async def _fetch_all(self, lat: float, lon: float, use_cache: bool):
        current = await self.client.fetch_current(lat, lon, use_cache=use_cache)
        forecast = await self.client.fetch_forecast(lat, lon, use_cache=use_cache)
        return current, forecast

    async def get_intelligence_for_tenant(
        self,
        session: Session,
        tenant_id: UUID,
        use_cache: bool = True,
        persist_signal: bool = False,
    ) -> WeatherIntelligenceReport:
        tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        report = await self.get_intelligence(
            tenant.latitude,
            tenant.longitude,
            business_type=tenant.business_type,
            tenant_id=tenant_id,
            use_cache=use_cache,
        )

        if persist_signal:
            self._persist_weather_signal(session, tenant_id, report)

        return report

    def _persist_weather_signal(
        self,
        session: Session,
        tenant_id: UUID,
        report: WeatherIntelligenceReport,
    ) -> None:
        value: dict[str, Any] = {
            "temp": report.current.temperature_c,
            "feels_like": report.current.feels_like_c,
            "condition": report.current.condition.value,
            "humidity": report.current.humidity_pct,
            "wind_speed": report.current.wind_speed_ms,
            "rain_intensity": report.current.rain_intensity.value,
            "precipitation_mm_1h": report.current.precipitation_mm_1h,
            "is_heavy_rain": report.current.is_heavy_rain,
            "heavy_rain_predicted_hours": (
                report.forecast.heavy_rain_within_hours if report.forecast else None
            ),
            "demand_adjustments": [a.model_dump() for a in report.demand_adjustments],
            "offers": [o.model_dump() for o in report.offers],
            "alerts": [a.model_dump() for a in report.alerts],
            "source": report.current.source,
        }
        session.add(
            DemandSignal(
                tenant_id=tenant_id,
                signal_type="weather",
                value=value,
            )
        )
        session.commit()

    def to_legacy_weather_dict(self, report: WeatherIntelligenceReport) -> dict[str, Any]:
        """Backward-compatible shape for pricing engine / agents."""
        c = report.current
        return {
            "temp": c.temperature_c,
            "condition": c.condition_label or c.condition.value,
            "humidity": c.humidity_pct,
            "wind_speed": c.wind_speed_ms,
            "is_heavy_rain": c.is_heavy_rain,
            "rain_intensity": c.rain_intensity.value,
            "source": c.source,
        }

    def invalidate(self, tenant_id: UUID, lat: float, lon: float) -> None:
        self.cache.invalidate_location(lat, lon)
        if self.cache._redis:
            from backend.services.weather_intelligence.cache import INTELLIGENCE_KEY

            self.cache._redis.delete(
                INTELLIGENCE_KEY.format(tenant_id=str(tenant_id))
            )


weather_intelligence_service = WeatherIntelligenceService()
