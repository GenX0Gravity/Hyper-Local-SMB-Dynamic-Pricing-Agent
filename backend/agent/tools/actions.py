"""Pricing action persistence and owner notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session

from backend.agent.state import PricingRecommendation, RecommendationType
from backend.models.recommendation import Recommendation
from backend.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


def persist_recommendations(
    session: Session,
    tenant_id: UUID,
    recs: list[PricingRecommendation],
    product_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Maps agent recommendations to legacy Recommendation rows."""
    saved = []
    catalog_by_id = {p["id"]: p for p in product_catalog}
    now = datetime.now(timezone.utc)

    for rec in recs:
        if rec.recommendation_type in (
            RecommendationType.BUNDLE,
            RecommendationType.HAPPY_HOUR,
        ):
            # Bundles / happy hour stored as metadata-only suggestions for now
            saved.append(
                {
                    "type": rec.recommendation_type.value,
                    "title": rec.title,
                    "persisted": False,
                }
            )
            continue

        for pid in rec.product_ids or []:
            product = catalog_by_id.get(str(pid)) or catalog_by_id.get(pid)
            if not product:
                continue
            prev = float(product.get("current_price", product.get("base_price", 0)))
            new_price = rec.suggested_price
            if new_price is None:
                new_price = round(prev * (1 + rec.adjustment_pct / 100), 2)

            row = Recommendation(
                tenant_id=tenant_id,
                product_id=UUID(str(pid)),
                recommended_price=new_price,
                previous_price=prev,
                reason=f"[{rec.recommendation_type.value}] {rec.description}",
                status="pending",
                expires_at=rec.valid_until or (now + timedelta(hours=12)),
            )
            session.add(row)
            saved.append(
                {
                    "type": rec.recommendation_type.value,
                    "product_id": str(pid),
                    "recommended_price": new_price,
                    "persisted": True,
                }
            )

    session.commit()
    return saved


async def send_owner_notification(
    phone: str | None,
    business_name: str,
    recommendations: list[PricingRecommendation],
    enabled: bool,
) -> dict[str, Any]:
    if not enabled or not phone:
        return {"ok": False, "skipped": True, "reason": "whatsapp_disabled"}

    lines = [f"PricePulse AI — {business_name}", "", "Today's pricing suggestions:"]
    for i, rec in enumerate(recommendations[:8], 1):
        lines.append(f"{i}. [{rec.recommendation_type.value}] {rec.title}")
        lines.append(f"   {rec.description}")

    body = "\n".join(lines)
    ok = await whatsapp_service.send_whatsapp_message(phone, body)
    return {"ok": ok, "body": body}
