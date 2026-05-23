"""Weekly and monthly analytics report builders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from backend.models.analytics_snapshot import AnalyticsSnapshot
from backend.services.analytics.metrics import MetricsCalculator
from backend.services.analytics.schemas import KPIMetrics, PeriodReport


class ReportBuilder:
    def __init__(self, calculator: MetricsCalculator | None = None):
        self.calculator = calculator or MetricsCalculator()

    def build_weekly(
        self,
        session: Session,
        tenant_id: UUID,
        weeks_back: int = 0,
    ) -> PeriodReport:
        now = datetime.now(timezone.utc)
        week_end = now - timedelta(weeks=weeks_back)
        week_start = week_end - timedelta(days=7)
        label = f"{week_start.strftime('%Y')}-W{week_start.isocalendar()[1]:02d}"
        return self._build(session, tenant_id, "weekly", week_start, week_end, label)

    def build_monthly(
        self,
        session: Session,
        tenant_id: UUID,
        months_back: int = 0,
    ) -> PeriodReport:
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        label = period_start.strftime("%Y-%m")
        return self._build(session, tenant_id, "monthly", period_start, period_end, label)

    def _build(
        self,
        session: Session,
        tenant_id: UUID,
        period_type: str,
        start: datetime,
        end: datetime,
        label: str,
    ) -> PeriodReport:
        kpis = self.calculator.compute(session, tenant_id, start, end)
        summary = self._narrative_summary(kpis, period_type, label)
        sections = {
            "recommendations": {
                "accepted": kpis.accepted_recommendations,
                "rejected": kpis.rejected_recommendations,
                "pending": kpis.pending_recommendations,
                "conversion_rate": kpis.conversion_rate,
            },
            "revenue": {
                "total": kpis.total_revenue,
                "baseline": kpis.baseline_revenue,
                "increase": kpis.revenue_increase,
                "increase_pct": kpis.revenue_increase_pct,
            },
            "accuracy": {
                "demand": kpis.demand_accuracy,
                "event_impact": kpis.event_impact_accuracy,
            },
        }
        return PeriodReport(
            tenant_id=tenant_id,
            period_type=period_type,
            period_start=start,
            period_end=end,
            label=label,
            kpis=kpis,
            summary=summary,
            sections=sections,
            generated_at=datetime.now(timezone.utc),
        )

    def persist(self, session: Session, report: PeriodReport) -> AnalyticsSnapshot:
        existing = session.exec(
            select(AnalyticsSnapshot).where(
                AnalyticsSnapshot.tenant_id == report.tenant_id,
                AnalyticsSnapshot.period_type == report.period_type,
                AnalyticsSnapshot.label == report.label,
            )
        ).first()

        payload = report.model_dump(mode="json")
        if existing:
            existing.metrics = payload
            existing.period_start = report.period_start
            existing.period_end = report.period_end
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        snap = AnalyticsSnapshot(
            tenant_id=report.tenant_id,
            period_type=report.period_type,
            period_start=report.period_start,
            period_end=report.period_end,
            label=report.label,
            metrics=payload,
        )
        session.add(snap)
        session.commit()
        session.refresh(snap)
        return snap

    def load_snapshots(
        self,
        session: Session,
        tenant_id: UUID,
        period_type: str,
        limit: int = 12,
    ) -> list[PeriodReport]:
        snaps = session.exec(
            select(AnalyticsSnapshot)
            .where(
                AnalyticsSnapshot.tenant_id == tenant_id,
                AnalyticsSnapshot.period_type == period_type,
            )
            .order_by(AnalyticsSnapshot.period_start.desc())  # type: ignore
        ).all()[:limit]

        reports = []
        for s in snaps:
            data = s.metrics or {}
            reports.append(PeriodReport.model_validate({**data, "id": s.id}))
        return reports

    @staticmethod
    def _narrative_summary(kpis: KPIMetrics, period_type: str, label: str) -> str:
        period_name = "week" if period_type == "weekly" else "month"
        lines = [
            f"{period_type.title()} report {label}:",
            f"Revenue increased by ${kpis.revenue_increase:.2f} ({kpis.revenue_increase_pct:.1f}%) vs baseline.",
            f"Recommendation conversion rate: {kpis.conversion_rate:.1f}% "
            f"({kpis.accepted_recommendations} accepted, {kpis.rejected_recommendations} rejected).",
            f"Demand forecast accuracy: {kpis.demand_accuracy:.1f}%. "
            f"Event impact accuracy: {kpis.event_impact_accuracy:.1f}%.",
        ]
        if kpis.conversion_rate >= 75:
            lines.append(f"Strong owner engagement this {period_name}.")
        elif kpis.rejected_recommendations > kpis.accepted_recommendations:
            lines.append("Consider reviewing pricing rules — rejection rate is elevated.")
        return " ".join(lines)

    def aggregate_kpis(self, reports: list[PeriodReport]) -> KPIMetrics | None:
        if not reports:
            return None
        n = len(reports)
        return KPIMetrics(
            revenue_increase=sum(r.kpis.revenue_increase for r in reports) / n,
            revenue_increase_pct=sum(r.kpis.revenue_increase_pct for r in reports) / n,
            conversion_rate=sum(r.kpis.conversion_rate for r in reports) / n,
            accepted_recommendations=sum(r.kpis.accepted_recommendations for r in reports),
            rejected_recommendations=sum(r.kpis.rejected_recommendations for r in reports),
            pending_recommendations=sum(r.kpis.pending_recommendations for r in reports),
            demand_accuracy=sum(r.kpis.demand_accuracy for r in reports) / n,
            event_impact_accuracy=sum(r.kpis.event_impact_accuracy for r in reports) / n,
            total_revenue=sum(r.kpis.total_revenue for r in reports),
            total_units_sold=sum(r.kpis.total_units_sold for r in reports),
            baseline_revenue=sum(r.kpis.baseline_revenue for r in reports),
        )
