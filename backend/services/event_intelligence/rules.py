"""Business rules — demand adjustments and alerts from classified events."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.core.config import settings
from backend.services.event_intelligence.schemas import (
    CategoryImpactSummary,
    ClassifiedEvent,
    DemandAdjustment,
    EventAlert,
    EventCategory,
    EventIntelligenceReport,
)


class EventRulesEngine:
    """Translates classified events + impact scores into pricing signals."""

    HIGH_IMPACT_THRESHOLD = 65.0
    CRITICAL_IMPACT_THRESHOLD = 80.0

    def evaluate(
        self,
        events: list[ClassifiedEvent],
        aggregate_impact_score: float,
        category_summary: list[CategoryImpactSummary],
        business_type: str = "cafe",
        tenant_id: str | None = None,
        latitude: float = 0.0,
        longitude: float = 0.0,
        pipeline_stats: dict | None = None,
        sources_queried: list[str] | None = None,
    ) -> EventIntelligenceReport:
        alerts: list[EventAlert] = []
        adjustments: list[DemandAdjustment] = []
        fired: list[str] = []

        if aggregate_impact_score >= self.CRITICAL_IMPACT_THRESHOLD:
            fired.append("critical_event_surge")
            self._apply_surge_rules(adjustments, alerts, events, boost_pct=25.0)
        elif aggregate_impact_score >= self.HIGH_IMPACT_THRESHOLD:
            fired.append("high_event_demand")
            self._apply_surge_rules(adjustments, alerts, events, boost_pct=15.0)

        for ev in events:
            if ev.category == EventCategory.IPL_MATCH and ev.impact_score >= 55:
                fired.append("ipl_match_boost")
                adjustments.append(
                    DemandAdjustment(
                        metric="beverage_demand_score",
                        adjusted_score=min(100.0, 50.0 + ev.impact_score * 0.4),
                        delta_pct=settings.EVENT_IPL_DEMAND_BOOST_PCT,
                        reason=f"IPL match nearby: {ev.name}",
                    )
                )
            elif ev.category == EventCategory.FOOTBALL_MATCH and ev.impact_score >= 50:
                fired.append("football_match_boost")
                adjustments.append(
                    DemandAdjustment(
                        metric="snacks_demand_score",
                        adjusted_score=min(100.0, 55.0 + ev.impact_score * 0.35),
                        delta_pct=settings.EVENT_FOOTBALL_DEMAND_BOOST_PCT,
                        reason=f"Football event: {ev.name}",
                    )
                )
            elif ev.category == EventCategory.DURGA_PUJA and ev.impact_score >= 45:
                fired.append("durga_puja_footfall")
                adjustments.append(
                    DemandAdjustment(
                        metric="festive_footfall_score",
                        adjusted_score=min(100.0, 60.0 + ev.impact_score * 0.3),
                        delta_pct=settings.EVENT_PUJA_DEMAND_BOOST_PCT,
                        reason="Durga Puja drives hyper-local foot traffic",
                    )
                )

        if any(s.category == EventCategory.PUBLIC_HOLIDAY for s in category_summary):
            fired.append("public_holiday_pattern")
            alerts.append(
                EventAlert(
                    severity="info",
                    code="public_holiday",
                    message="Public holiday detected — review staffing and inventory",
                )
            )

        nearest = events[0] if events else None
        if nearest and nearest.hours_until_start is not None and nearest.hours_until_start <= 12:
            fired.append("imminent_event")
            alerts.append(
                EventAlert(
                    severity="warning",
                    code="event_imminent",
                    message=f"High-impact event in {nearest.hours_until_start:.0f}h: {nearest.name}",
                    related_event_id=nearest.external_id,
                )
            )

        return EventIntelligenceReport(
            tenant_id=tenant_id,
            location={"latitude": latitude, "longitude": longitude},
            events=events,
            aggregate_impact_score=aggregate_impact_score,
            category_summary=category_summary,
            demand_adjustments=adjustments,
            alerts=alerts,
            rules_fired=fired,
            sources_queried=sources_queried or [],
            pipeline_stats=pipeline_stats or {},
            generated_at=datetime.now(timezone.utc),
        )

    def _apply_surge_rules(
        self,
        adjustments: list[DemandAdjustment],
        alerts: list[EventAlert],
        events: list[ClassifiedEvent],
        boost_pct: float,
    ) -> None:
        top = events[0] if events else None
        alerts.append(
            EventAlert(
                severity="critical" if boost_pct >= 20 else "warning",
                code="event_demand_surge",
                message=f"Event impact surge — composite score elevated",
                related_event_id=top.external_id if top else None,
            )
        )
        adjustments.append(
            DemandAdjustment(
                metric="foot_traffic_demand_score",
                adjusted_score=min(100.0, 50.0 + boost_pct * 2),
                delta_pct=boost_pct,
                reason="Multiple high-impact local events detected",
            )
        )
