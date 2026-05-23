"""Analytics reporting APIs — KPI dashboard, weekly & monthly reports."""

from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.api.deps import get_current_tenant_id, get_db
from backend.models.product import Product
from backend.models.recommendation import Recommendation
from backend.models.rule import PricingRule
from backend.models.sales_history import SalesHistory
from backend.services.analytics import (
    KPIDashboard,
    PeriodReport,
    ReportsBundle,
    analytics_service,
)

router = APIRouter()


# --- Legacy schemas (backward compatible) ---
class OverviewStats(BaseModel):
    revenue_lift: float
    applied_recommendations: int
    active_rules: int
    capture_rate: float
    total_sales_count: int
    total_revenue: float


class ForecastPoint(BaseModel):
    date: str
    expected_sales_units: int
    forecast_confidence: float
    influencing_factor: str


class CategoryForecast(BaseModel):
    category: str
    forecast: List[ForecastPoint]


# --- KPI & reporting endpoints ---

@router.get("/kpi", response_model=KPIDashboard)
def get_kpi_dashboard(
    lookback_days: int = Query(30, ge=7, le=90),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    KPI dashboard: revenue increase, conversion rate, accepted/rejected recs,
    demand accuracy, event impact accuracy, and daily trends.
    """
    return analytics_service.get_kpi_dashboard(db, tenant_id, lookback_days=lookback_days)


@router.get("/reports/weekly", response_model=ReportsBundle)
def get_weekly_reports(
    weeks: int = Query(4, ge=1, le=12),
    persist: bool = Query(False, description="Save snapshots to database"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Weekly analytics reports for the last N weeks."""
    return analytics_service.get_weekly_reports(db, tenant_id, weeks=weeks, persist=persist)


@router.get("/reports/monthly", response_model=ReportsBundle)
def get_monthly_reports(
    months: int = Query(6, ge=1, le=24),
    persist: bool = Query(False),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Monthly analytics reports for the last N months."""
    return analytics_service.get_monthly_reports(db, tenant_id, months=months, persist=persist)


@router.post("/reports/generate", response_model=PeriodReport)
def generate_period_report(
    period_type: str = Query(..., pattern="^(weekly|monthly)$"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Generate and persist the current weekly or monthly report."""
    return analytics_service.generate_and_persist_period(db, tenant_id, period_type)


@router.get("/overview", response_model=OverviewStats)
def get_dashboard_overview(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Legacy overview — maps to KPI dashboard metrics."""
    dashboard = analytics_service.get_kpi_dashboard(db, tenant_id, lookback_days=30)
    k = dashboard.kpis

    active_rules_count = len(
        db.exec(
            select(PricingRule).where(
                PricingRule.tenant_id == tenant_id,
                PricingRule.is_active == True,
            )
        ).all()
    )

    return OverviewStats(
        revenue_lift=k.revenue_increase,
        applied_recommendations=k.accepted_recommendations,
        active_rules=active_rules_count,
        capture_rate=k.conversion_rate,
        total_sales_count=k.total_units_sold,
        total_revenue=k.total_revenue,
    )


@router.get("/demand-forecast", response_model=List[CategoryForecast])
def get_demand_forecasting(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """7-day category demand forecast (legacy endpoint)."""
    categories = db.exec(
        select(Product.category).where(Product.tenant_id == tenant_id).distinct()
    ).all()

    if not categories or None in categories:
        categories = ["Beverages", "Merchandise", "Apparel"]
    else:
        categories = [c for c in categories if c]

    weather_forecast = [
        {"day": 0, "cond": "Sunny", "temp": 26},
        {"day": 1, "cond": "Rainy", "temp": 14},
        {"day": 2, "cond": "Rainy", "temp": 12},
        {"day": 3, "cond": "Cloudy", "temp": 18},
        {"day": 4, "cond": "Sunny", "temp": 24},
        {"day": 5, "cond": "Heatwave", "temp": 38},
        {"day": 6, "cond": "Sunny", "temp": 28},
    ]

    forecasts = []
    now = datetime.now(timezone.utc)

    for cat in categories:
        points = []
        for index, wf in enumerate(weather_forecast):
            target_date = now + timedelta(days=index)
            date_str = target_date.strftime("%Y-%m-%d")

            if "cafe" in (cat or "").lower() or "beverage" in (cat or "").lower():
                base_units = 150
                if wf["cond"] == "Rainy" or wf["temp"] < 15:
                    expected = base_units * 1.25
                    factor = "Rainy weather (+25% Hot Drinks)"
                elif wf["cond"] == "Heatwave":
                    expected = base_units * 1.4
                    factor = "Heatwave Alert (+40% Iced Drinks)"
                else:
                    expected = base_units
                    factor = "Normal Time-of-Week"
            elif "boutique" in (cat or "").lower() or "apparel" in (cat or "").lower():
                base_units = 45
                if wf["cond"] == "Rainy":
                    expected = base_units * 0.7
                    factor = "Rainy weather (-30% Store Traffic)"
                elif wf["cond"] == "Sunny":
                    expected = base_units * 1.3
                    factor = "Sunny Weekend (+30% Foot Traffic)"
                else:
                    expected = base_units
                    factor = "Normal Time-of-Week"
            else:
                base_units = 60
                expected = base_units * 1.1 if wf["cond"] == "Rainy" else base_units
                factor = "Rainy day (+10%)" if wf["cond"] == "Rainy" else "Stable Demand"

            points.append(
                ForecastPoint(
                    date=date_str,
                    expected_sales_units=int(expected),
                    forecast_confidence=round(0.85 - (index * 0.04), 2),
                    influencing_factor=factor,
                )
            )

        forecasts.append(CategoryForecast(category=cat, forecast=points))

    return forecasts
