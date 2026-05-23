"""Weather Intelligence API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from backend.api.deps import get_current_tenant_id, get_db
from backend.services.weather_intelligence.schemas import WeatherIntelligenceReport
from backend.services.weather_intelligence.service import weather_intelligence_service

router = APIRouter()


@router.get("/intelligence", response_model=WeatherIntelligenceReport)
async def get_weather_intelligence(
    refresh: bool = Query(False, description="Bypass Redis cache"),
    persist: bool = Query(False, description="Save signal to database"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Full weather intelligence report: current conditions, forecast,
    demand score adjustments, and weather-specific offers.
    """
    try:
        return await weather_intelligence_service.get_intelligence_for_tenant(
            db,
            tenant_id,
            use_cache=not refresh,
            persist_signal=persist,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/intelligence/refresh", response_model=WeatherIntelligenceReport)
async def refresh_weather_intelligence(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Force refresh from OpenWeatherMap and persist signal."""
    from sqlmodel import select
    from backend.models.tenant import Tenant

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    weather_intelligence_service.invalidate(
        tenant_id, tenant.latitude, tenant.longitude
    )
    return await weather_intelligence_service.get_intelligence_for_tenant(
        db, tenant_id, use_cache=False, persist_signal=True,
    )


@router.get("/monitor")
async def monitor_weather_metrics(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Lightweight monitor endpoint — rain, temp, humidity, wind only."""
    report = await weather_intelligence_service.get_intelligence_for_tenant(
        db, tenant_id, use_cache=True, persist_signal=False,
    )
    c = report.current
    return {
        "rain": {
            "intensity": c.rain_intensity.value,
            "precipitation_mm_1h": c.precipitation_mm_1h,
            "is_raining": c.is_raining,
            "is_heavy_rain": c.is_heavy_rain,
            "heavy_rain_predicted_within_hours": (
                report.forecast.heavy_rain_within_hours if report.forecast else None
            ),
        },
        "temperature_c": c.temperature_c,
        "humidity_pct": c.humidity_pct,
        "wind_speed_ms": c.wind_speed_ms,
        "cache_hit": report.cache_hit,
        "recorded_at": c.recorded_at.isoformat(),
    }
