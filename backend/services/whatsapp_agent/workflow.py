"""Approval workflow — approve, reject, auto-approve recommendations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from backend.models.product import Product
from backend.models.recommendation import Recommendation, RecommendationAudit
from backend.models.tenant import Tenant
from backend.services.whatsapp_agent.templates import MessageTemplates

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """Shared approve/reject logic for API and WhatsApp agent."""

    def approve(
        self,
        session: Session,
        recommendation_id: UUID,
        *,
        changed_by: UUID | None = None,
        via: str = "whatsapp",
    ) -> dict[str, Any]:
        rec = session.get(Recommendation, recommendation_id)
        if not rec:
            return {"ok": False, "error": "not_found"}
        if rec.status != "pending":
            return {"ok": False, "error": f"invalid_status:{rec.status}"}

        product = session.get(Product, rec.product_id)
        if not product:
            return {"ok": False, "error": "product_not_found"}

        rec.previous_price = product.current_price
        product.current_price = rec.recommended_price
        product.updated_at = datetime.now(timezone.utc)
        rec.status = "approved"
        session.add(product)
        session.add(rec)
        session.add(
            RecommendationAudit(
                recommendation_id=rec.id,
                action=f"approved_{via}",
                changed_by=changed_by,
            )
        )
        session.commit()
        session.refresh(product)

        tenant = session.get(Tenant, rec.tenant_id)
        currency = tenant.currency if tenant else "USD"
        return {
            "ok": True,
            "product_name": product.name,
            "new_price": product.current_price,
            "message": MessageTemplates.approval_confirmed(
                product.name, product.current_price, currency
            ),
        }

    def reject(
        self,
        session: Session,
        recommendation_id: UUID,
        *,
        changed_by: UUID | None = None,
        via: str = "whatsapp",
    ) -> dict[str, Any]:
        rec = session.get(Recommendation, recommendation_id)
        if not rec:
            return {"ok": False, "error": "not_found"}
        if rec.status != "pending":
            return {"ok": False, "error": f"invalid_status:{rec.status}"}

        product = session.get(Product, rec.product_id)
        rec.status = "rejected"
        session.add(rec)
        session.add(
            RecommendationAudit(
                recommendation_id=rec.id,
                action=f"rejected_{via}",
                changed_by=changed_by,
            )
        )
        session.commit()

        name = product.name if product else "product"
        return {
            "ok": True,
            "product_name": name,
            "message": MessageTemplates.rejection_confirmed(name),
        }

    def auto_approve_pending(
        self, session: Session, tenant_id: UUID, via: str = "auto"
    ) -> list[dict[str, Any]]:
        pending = session.exec(
            select(Recommendation).where(
                Recommendation.tenant_id == tenant_id,
                Recommendation.status == "pending",
            )
        ).all()
        results = []
        for rec in pending:
            result = self.approve(session, rec.id, via=via)
            results.append(result)
        return results

    def count_by_status(self, session: Session, tenant_id: UUID) -> dict[str, int]:
        from sqlalchemy import func

        rows = session.exec(
            select(Recommendation.status, func.count())
            .where(Recommendation.tenant_id == tenant_id)
            .group_by(Recommendation.status)
        ).all()
        counts = {status: count for status, count in rows}
        return {
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
        }
