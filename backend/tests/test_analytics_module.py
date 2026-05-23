"""Tests for analytics module."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.services.analytics.metrics import MetricsCalculator
from backend.services.analytics.reports import ReportBuilder
from backend.services.analytics.schemas import KPIMetrics


def test_kpi_metrics_defaults():
    m = KPIMetrics(
        revenue_increase=100.0,
        revenue_increase_pct=8.0,
        conversion_rate=75.0,
        accepted_recommendations=10,
        rejected_recommendations=2,
        demand_accuracy=80.0,
        event_impact_accuracy=72.0,
    )
    assert m.conversion_rate == 75.0
    assert m.pending_recommendations == 0


def test_report_narrative_summary():
    kpis = KPIMetrics(
        revenue_increase=200.0,
        revenue_increase_pct=10.0,
        conversion_rate=80.0,
        accepted_recommendations=8,
        rejected_recommendations=2,
        demand_accuracy=78.0,
        event_impact_accuracy=71.0,
    )
    text = ReportBuilder._narrative_summary(kpis, "weekly", "2026-W20")
    assert "Revenue increased" in text
    assert "conversion" in text.lower()


def test_aggregate_kpis():
    from backend.services.analytics.schemas import PeriodReport

    kpis = KPIMetrics(
        revenue_increase=100,
        revenue_increase_pct=5,
        conversion_rate=50,
        accepted_recommendations=5,
        rejected_recommendations=5,
        demand_accuracy=70,
        event_impact_accuracy=70,
    )
    reports = [
        PeriodReport(
            tenant_id=uuid4(),
            period_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            label="W1",
            kpis=kpis,
            summary="",
            generated_at=datetime.now(timezone.utc),
        )
    ]
    agg = ReportBuilder().aggregate_kpis(reports)
    assert agg is not None
    assert agg.accepted_recommendations == 5
