"""Build and send pricing recommendation WhatsApp notifications."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from backend.models.product import Product
from backend.models.recommendation import Recommendation
from backend.models.tenant import Tenant
from backend.services.whatsapp_agent.session_store import WhatsAppSessionStore
from backend.services.whatsapp_agent.templates import MessageTemplates
from backend.services.whatsapp_agent.twilio_client import TwilioWhatsAppClient
from backend.services.whatsapp_agent.workflow import ApprovalWorkflow

logger = logging.getLogger(__name__)


class RecommendationNotifier:
    def __init__(
        self,
        client: TwilioWhatsAppClient | None = None,
        store: WhatsAppSessionStore | None = None,
        workflow: ApprovalWorkflow | None = None,
    ):
        self.client = client or TwilioWhatsAppClient()
        self.store = store or WhatsAppSessionStore()
        self.workflow = workflow or ApprovalWorkflow()

    async def send_recommendations(
        self,
        session: Session,
        tenant_id: UUID,
        *,
        weather_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tenant = session.get(Tenant, tenant_id)
        if not tenant or not tenant.whatsapp_enabled or not tenant.whatsapp_phone:
            return {"ok": False, "skipped": True, "reason": "whatsapp_disabled"}

        pending = session.exec(
            select(Recommendation).where(
                Recommendation.tenant_id == tenant_id,
                Recommendation.status == "pending",
            )
        ).all()

        if not pending:
            return {"ok": True, "sent": 0, "message": "no_pending"}

        auto = getattr(tenant, "whatsapp_auto_approve", False)
        if auto:
            results = self.workflow.auto_approve_pending(session, tenant_id, via="auto")
            body = (
                f"*{MessageTemplates.BRAND}* — {tenant.name}\n\n"
                f"Auto-approved *{len(results)}* pricing update(s).\n"
                + "\n".join(
                    f"• {r.get('product_name')}: ${r.get('new_price', 0):.2f}"
                    for r in results
                    if r.get("ok")
                )
            )
            await self.client.send_message(tenant.whatsapp_phone, body)
            self.store.clear_pending(self.client.normalize_phone_key(tenant.whatsapp_phone))
            return {"ok": True, "sent": 1, "auto_approved": len(results)}

        phone_key = self.client.normalize_phone_key(tenant.whatsapp_phone)
        self.store.set_tenant(phone_key, str(tenant_id))

        items: list[dict[str, Any]] = []
        messages: list[str] = []

        if weather_context:
            headline = self._weather_headline(weather_context)
            if headline:
                messages.append(headline)

        header = MessageTemplates.batch_header(tenant.name, len(pending))
        messages.append(header)

        for i, rec in enumerate(pending[:8], 1):
            product = session.get(Product, rec.product_id)
            if not product:
                continue
            discount, increase = self._parse_adjustment(rec, product)
            headline = self._insight_line(rec.reason)
            msg = MessageTemplates.pricing_recommendation(
                store_name=tenant.name,
                headline=headline,
                product_name=product.name,
                category=product.category,
                current_price=product.current_price,
                recommended_price=rec.recommended_price,
                discount_pct=discount,
                increase_pct=increase,
                currency=tenant.currency,
                index=i,
                total=min(len(pending), 8),
            )
            messages.append(msg)
            items.append(
                {
                    "index": i,
                    "recommendation_id": str(rec.id),
                    "product_name": product.name,
                }
            )

        messages.append(MessageTemplates.batch_footer(auto_approve=False))
        self.store.set_pending(phone_key, items)

        sent = 0
        for msg in messages:
            result = await self.client.send_message(tenant.whatsapp_phone, msg)
            if result.get("ok"):
                sent += 1

        return {"ok": True, "sent": sent, "pending_count": len(pending)}

    async def send_weather_alert(
        self,
        session: Session,
        tenant_id: UUID,
        *,
        condition: str,
        time_label: str,
        discount_pct: float,
        category: str = "tea & hot beverages",
    ) -> dict[str, Any]:
        tenant = session.get(Tenant, tenant_id)
        if not tenant or not tenant.whatsapp_enabled or not tenant.whatsapp_phone:
            return {"ok": False, "skipped": True}

        body = MessageTemplates.weather_alert(
            store_name=tenant.name,
            condition=condition,
            time_label=time_label,
            discount_pct=discount_pct,
            category=category,
        )
        return await self.client.send_message(tenant.whatsapp_phone, body)

    @staticmethod
    def _parse_adjustment(rec: Recommendation, product: Product) -> tuple[float, float]:
        if product.current_price <= 0:
            return 0.0, 0.0
        delta_pct = (
            (rec.recommended_price - product.current_price) / product.current_price
        ) * 100.0
        if delta_pct < -0.5:
            return abs(delta_pct), 0.0
        if delta_pct > 0.5:
            return 0.0, delta_pct
        m = re.search(r"Discount:\s*([\d.]+)%", rec.reason or "")
        if m:
            return float(m.group(1)), 0.0
        m = re.search(r"increase:\s*([\d.]+)%", rec.reason or "", re.I)
        if m:
            return 0.0, float(m.group(1))
        return 0.0, 0.0

    @staticmethod
    def _insight_line(reason: str | None) -> str:
        if not reason:
            return "Pricing opportunity detected"
        first = reason.split("\n")[0].strip()
        if len(first) > 80:
            return first[:77] + "..."
        return first

    @staticmethod
    def _weather_headline(ctx: dict[str, Any]) -> str | None:
        if ctx.get("is_heavy_rain") or "heavy" in str(ctx.get("condition", "")).lower():
            time_lbl = ctx.get("heavy_rain_time") or "at 4 PM"
            return MessageTemplates.weather_alert(
                store_name=ctx.get("store_name", "your store"),
                condition="Heavy rain",
                time_label=time_lbl,
                discount_pct=ctx.get("suggested_discount", 20.0),
                category=ctx.get("category", "tea & hot beverages"),
            )
        return None
