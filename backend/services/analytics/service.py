"""Analytics module facade — KPI dashboard and periodic reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session

from backend.services.analytics.metrics import MetricsCalculator
from backend.services.analytics.reports import ReportBuilder
from backend.services.analytics.schemas import KPIDashboard, PeriodReport, ReportsBundle


class AnalyticsService:
    def __init__(
        self,
        calculator: MetricsCalculator | None = None,
        reports: ReportBuilder | None = None,
    ):
        self.calculator = calculator or MetricsCalculator()
        self.reports = reports or ReportBuilder(self.calculator)

    def get_kpi_dashboard(
        self,
        session: Session,
        tenant_id: UUID,
        lookback_days: int = 30,
    ) -> KPIDashboard:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days)
        kpis = self.calculator.compute(session, tenant_id, start, end)
        trends = self.calculator.compute_daily_trends(
            session, tenant_id, days=min(lookback_days, 14)
        )
        highlights = self._highlights(kpis)
        return KPIDashboard(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            generated_at=end,
            kpis=kpis,
            trends=trends,
            highlights=highlights,
        )

    def get_weekly_reports(
        self,
        session: Session,
        tenant_id: UUID,
        weeks: int = 4,
        persist: bool = False,
    ) -> ReportsBundle:
        built: list[PeriodReport] = []
        for w in range(weeks):
            report = self.reports.build_weekly(session, tenant_id, weeks_back=w)
            if persist:
                snap = self.reports.persist(session, report)
                report.id = snap.id
            built.append(report)

        if persist:
            stored = self.reports.load_snapshots(session, tenant_id, "weekly", limit=weeks)
            reports = stored or built
        else:
            reports = built
        return ReportsBundle(
            period_type="weekly",
            reports=reports,
            aggregate=self.reports.aggregate_kpis(reports),
        )

    def get_monthly_reports(
        self,
        session: Session,
        tenant_id: UUID,
        months: int = 6,
        persist: bool = False,
    ) -> ReportsBundle:
        built: list[PeriodReport] = []
        for m in range(months):
            report = self.reports.build_monthly(session, tenant_id, months_back=m)
            if persist:
                snap = self.reports.persist(session, report)
                report.id = snap.id
            built.append(report)

        if persist:
            stored = self.reports.load_snapshots(session, tenant_id, "monthly", limit=months)
            reports = stored or built
        else:
            reports = built
        return ReportsBundle(
            period_type="monthly",
            reports=reports,
            aggregate=self.reports.aggregate_kpis(reports),
        )

    def generate_and_persist_period(
        self,
        session: Session,
        tenant_id: UUID,
        period_type: str,
    ) -> PeriodReport:
        if period_type == "weekly":
            report = self.reports.build_weekly(session, tenant_id, weeks_back=0)
        else:
            report = self.reports.build_monthly(session, tenant_id, months_back=0)
        snap = self.reports.persist(session, report)
        report.id = snap.id
        return report

    @staticmethod
    def _highlights(kpis) -> list[str]:
        highlights = []
        if kpis.revenue_increase_pct >= 5:
            highlights.append(
                f"Revenue up {kpis.revenue_increase_pct:.1f}% from dynamic pricing."
            )
        if kpis.conversion_rate >= 70:
            highlights.append(
                f"High recommendation acceptance ({kpis.conversion_rate:.0f}% conversion)."
            )
        if kpis.demand_accuracy >= 75:
            highlights.append(f"Demand forecasts accurate at {kpis.demand_accuracy:.0f}%.")
        if kpis.event_impact_accuracy >= 70:
            highlights.append(
                f"Event impact predictions reliable ({kpis.event_impact_accuracy:.0f}%)."
            )
        if kpis.rejected_recommendations > kpis.accepted_recommendations:
            highlights.append("More rejections than acceptances — tune pricing rules.")
        if not highlights:
            highlights.append("Collect more sales data to improve analytics confidence.")
        return highlights


analytics_service = AnalyticsService()
