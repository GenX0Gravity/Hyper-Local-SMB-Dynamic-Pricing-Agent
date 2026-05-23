"""Analytics module — KPIs, trends, weekly/monthly reports."""

from backend.services.analytics.service import analytics_service
from backend.services.analytics.schemas import KPIDashboard, KPIMetrics, PeriodReport, ReportsBundle

__all__ = [
    "analytics_service",
    "KPIDashboard",
    "KPIMetrics",
    "PeriodReport",
    "ReportsBundle",
]
