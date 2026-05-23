"""Event Intelligence API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from backend.api.deps import get_current_tenant_id, get_db
from backend.models.tenant import Tenant
from backend.services.event_intelligence.schemas import EventIntelligenceReport
from backend.services.event_intelligence.service import event_intelligence_service

router = APIRouter()


@router.get("/intelligence", response_model=EventIntelligenceReport)
async def get_event_intelligence(
    refresh: bool = Query(False, description="Bypass Redis cache"),
    persist: bool = Query(False, description="Save event signals to database"),
    radius_km: float = Query(2.0, ge=0.5, le=25.0, description="Search radius in km"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Full event intelligence report: classified events (IPL, football, Durga Puja,
    college fests, holidays, local), Event Impact Score, and demand adjustments.
    """
    try:
        return await event_intelligence_service.get_intelligence_for_tenant(
            db,
            tenant_id,
            use_cache=not refresh,
            persist_signal=persist,
            radius_km=radius_km,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/intelligence/refresh", response_model=EventIntelligenceReport)
async def refresh_event_intelligence(
    radius_km: float = Query(2.0, ge=0.5, le=25.0),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Force refresh from all data sources and persist signals."""
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    event_intelligence_service.invalidate(
        tenant_id, tenant.latitude, tenant.longitude
    )
    return await event_intelligence_service.get_intelligence_for_tenant(
        db, tenant_id, use_cache=False, persist_signal=True, radius_km=radius_km
    )


@router.get("/monitor")
async def monitor_event_metrics(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Lightweight monitor — aggregate impact, upcoming count, top event."""
    report = await event_intelligence_service.get_intelligence_for_tenant(
        db, tenant_id, use_cache=True, persist_signal=False
    )
    top = report.events[0] if report.events else None
    monitored = {
        "ipl_match": 0,
        "football_match": 0,
        "durga_puja": 0,
        "college_festival": 0,
        "public_holiday": 0,
        "local_event": 0,
    }
    for ev in report.events:
        key = ev.category.value
        if key in monitored:
            monitored[key] += 1

    return {
        "aggregate_impact_score": report.aggregate_impact_score,
        "upcoming_event_count": len(report.events),
        "top_event": (
            {
                "name": top.name,
                "category": top.category.value,
                "impact_score": top.impact_score,
                "hours_until_start": top.hours_until_start,
            }
            if top
            else None
        ),
        "monitored_categories": monitored,
        "sources_queried": report.sources_queried,
        "cache_hit": report.cache_hit,
        "generated_at": report.generated_at.isoformat(),
    }


@router.get("/impact-score")
async def get_aggregate_impact_score(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Returns composite Event Impact Score (0–100) only."""
    report = await event_intelligence_service.get_intelligence_for_tenant(
        db, tenant_id, use_cache=True, persist_signal=False
    )
    return {
        "aggregate_impact_score": report.aggregate_impact_score,
        "event_count": len(report.events),
        "cache_hit": report.cache_hit,
    }
