"""Event Intelligence Service — orchestrates pipeline, cache, and rules."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select

from backend.models.signal import DemandSignal
from backend.models.tenant import Tenant
from backend.services.event_intelligence.cache import EventCache
from backend.services.event_intelligence.pipeline import EventDataPipeline
from backend.services.event_intelligence.rules import EventRulesEngine
from backend.services.event_intelligence.schemas import EventIntelligenceReport

logger = logging.getLogger(__name__)


class EventIntelligenceService:
    def __init__(
        self,
        cache: EventCache | None = None,
        pipeline: EventDataPipeline | None = None,
        rules: EventRulesEngine | None = None,
    ):
        self.cache = cache or EventCache()
        self.pipeline = pipeline or EventDataPipeline()
        self.rules = rules or EventRulesEngine()

    async def get_intelligence(
        self,
        latitude: float,
        longitude: float,
        business_type: str = "cafe",
        tenant_id: UUID | None = None,
        use_cache: bool = True,
        radius_km: float = 2.0,
        city: str = "local",
    ) -> EventIntelligenceReport:
        tid = str(tenant_id) if tenant_id else None
        if use_cache and tid:
            cached = self.cache.get_intelligence(tid)
            if cached:
                report = EventIntelligenceReport.model_validate(cached)
                return report.model_copy(update={"cache_hit": True})

        classified, stats = await self.pipeline.run(
            latitude, longitude, radius_km=radius_km, city=city
        )
        aggregate = self.pipeline.scorer.aggregate_impact(classified)
        summary = self.pipeline.summarize_by_category(classified)

        report = self.rules.evaluate(
            events=classified,
            aggregate_impact_score=aggregate,
            category_summary=summary,
            business_type=business_type,
            tenant_id=tid,
            latitude=latitude,
            longitude=longitude,
            pipeline_stats=stats,
            sources_queried=stats.get("sources", []),
        )

        if tid:
            self.cache.set_intelligence(tid, report.model_dump(mode="json"))
        return report

    async def get_intelligence_for_tenant(
        self,
        session: Session,
        tenant_id: UUID,
        use_cache: bool = True,
        persist_signal: bool = False,
        radius_km: float = 2.0,
    ) -> EventIntelligenceReport:
        tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        report = await self.get_intelligence(
            tenant.latitude,
            tenant.longitude,
            business_type=tenant.business_type,
            tenant_id=tenant_id,
            use_cache=use_cache,
            radius_km=radius_km,
            city=tenant.name,
        )

        if persist_signal:
            self._persist_event_signals(session, tenant_id, report)

        return report

    def _persist_event_signals(
        self,
        session: Session,
        tenant_id: UUID,
        report: EventIntelligenceReport,
    ) -> None:
        for ev in report.events:
            value: dict[str, Any] = {
                "name": ev.name,
                "category": ev.category.value,
                "category_label": ev.category_label,
                "attendance": ev.attendance_est,
                "attendance_est": ev.attendance_est,
                "distance_km": ev.distance_km,
                "impact_score": ev.impact_score,
                "start_time": ev.start_at.isoformat() if ev.start_at else None,
                "end_time": ev.end_at.isoformat() if ev.end_at else None,
                "source": ev.source.value,
                "aggregate_impact_score": report.aggregate_impact_score,
            }
            session.add(
                DemandSignal(
                    tenant_id=tenant_id,
                    signal_type="event",
                    value=value,
                )
            )
        session.commit()

    def to_legacy_event_list(self, report: EventIntelligenceReport) -> list[dict[str, Any]]:
        """Backward-compatible shape for pricing engine / agents."""
        return [
            {
                "name": ev.name,
                "category": ev.category.value,
                "attendance": ev.attendance_est,
                "distance_km": ev.distance_km,
                "start_time": ev.start_at.isoformat() if ev.start_at else None,
                "end_time": ev.end_at.isoformat() if ev.end_at else None,
                "impact_score": ev.impact_score,
                "source": ev.source.value,
            }
            for ev in report.events
        ]

    def invalidate(self, tenant_id: UUID, lat: float, lon: float) -> None:
        self.cache.invalidate(str(tenant_id), lat, lon)


event_intelligence_service = EventIntelligenceService()
