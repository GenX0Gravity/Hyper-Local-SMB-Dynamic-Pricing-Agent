"""Signal collection tools — each returns a dict and never raises to the graph."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Session, select, func

from backend.models.product import Product
from backend.models.sales_history import SalesHistory
from backend.services.event_service import event_service
from backend.services.footfall_service import footfall_service
from backend.services.news_service import news_service
from backend.services.weather_service import weather_service

logger = logging.getLogger(__name__)


async def fetch_weather(latitude: float, longitude: float) -> dict[str, Any]:
    try:
        data = await weather_service.get_current_weather(latitude, longitude)
        return {"ok": True, "data": data}
    except Exception as exc:
        logger.exception("fetch_weather failed")
        return {"ok": False, "error": str(exc)}


async def fetch_footfall(latitude: float, longitude: float) -> dict[str, Any]:
    try:
        data = await footfall_service.get_popular_times(latitude, longitude)
        return {"ok": True, "data": data}
    except Exception as exc:
        logger.exception("fetch_footfall failed")
        return {"ok": False, "error": str(exc)}


async def fetch_news(city: str = "local") -> dict[str, Any]:
    try:
        articles = await news_service.get_local_headlines(city=city)
        return {"ok": True, "data": articles}
    except Exception as exc:
        logger.exception("fetch_news failed")
        return {"ok": False, "error": str(exc)}


async def fetch_events(latitude: float, longitude: float) -> dict[str, Any]:
    try:
        events = await event_service.get_upcoming_events(latitude, longitude)
        return {"ok": True, "data": events}
    except Exception as exc:
        logger.exception("fetch_events failed")
        return {"ok": False, "error": str(exc)}


def fetch_sales_history(
    session: Session,
    tenant_id: UUID,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """Synchronous DB tool — aggregates historical sales per product."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        rows = session.exec(
            select(
                SalesHistory.product_id,
                func.sum(SalesHistory.quantity).label("units"),
                func.avg(SalesHistory.price_sold).label("avg_price"),
            )
            .where(SalesHistory.tenant_id == tenant_id, SalesHistory.sold_at >= since)
            .group_by(SalesHistory.product_id)
        ).all()

        products = session.exec(
            select(Product).where(Product.tenant_id == tenant_id)
        ).all()
        by_id = {p.id: p for p in products}

        per_product = []
        total_units = 0
        for row in rows:
            pid, units, avg_price = row
            total_units += int(units or 0)
            product = by_id.get(pid)
            per_product.append(
                {
                    "product_id": str(pid),
                    "name": product.name if product else "unknown",
                    "units_sold": int(units or 0),
                    "avg_price": float(avg_price or 0),
                    "category": product.category if product else None,
                }
            )

        return {
            "ok": True,
            "data": {
                "lookback_days": lookback_days,
                "total_units": total_units,
                "per_product": per_product,
                "product_count": len(products),
            },
        }
    except Exception as exc:
        logger.exception("fetch_sales_history failed")
        return {"ok": False, "error": str(exc)}
