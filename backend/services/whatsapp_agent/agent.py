"""WhatsApp Business Agent — inbound webhooks and outbound notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from backend.core.config import settings
from backend.models.recommendation import Recommendation
from backend.models.tenant import Tenant
from backend.services.whatsapp_agent.notifier import RecommendationNotifier
from backend.services.whatsapp_agent.parser import CommandType, InboundCommandParser
from backend.services.whatsapp_agent.session_store import WhatsAppSessionStore
from backend.services.whatsapp_agent.templates import MessageTemplates
from backend.services.whatsapp_agent.twilio_client import TwilioWhatsAppClient
from backend.services.whatsapp_agent.workflow import ApprovalWorkflow

logger = logging.getLogger(__name__)


class WhatsAppBusinessAgent:
    def __init__(
        self,
        client: TwilioWhatsAppClient | None = None,
        store: WhatsAppSessionStore | None = None,
        parser: InboundCommandParser | None = None,
        workflow: ApprovalWorkflow | None = None,
        notifier: RecommendationNotifier | None = None,
    ):
        self.client = client or TwilioWhatsAppClient()
        self.store = store or WhatsAppSessionStore()
        self.parser = parser or InboundCommandParser()
        self.workflow = workflow or ApprovalWorkflow()
        self.notifier = notifier or RecommendationNotifier(
            self.client, self.store, self.workflow
        )

    def resolve_tenant(
        self, session: Session, from_number: str
    ) -> Tenant | None:
        phone_key = self.client.normalize_phone_key(from_number)
        tid = self.store.get_tenant(phone_key)
        if tid:
            return session.get(Tenant, UUID(tid))

        digits = phone_key
        tenants = session.exec(select(Tenant)).all()
        for t in tenants:
            if not t.whatsapp_phone:
                continue
            t_key = self.client.normalize_phone_key(t.whatsapp_phone)
            if t_key == digits or t_key.endswith(digits) or digits.endswith(t_key):
                self.store.set_tenant(phone_key, str(t.id))
                return t
        return None

    async def handle_inbound(
        self,
        session: Session,
        from_number: str,
        body: str,
    ) -> str:
        """Process inbound message; return reply text (TwiML body)."""
        tenant = self.resolve_tenant(session, from_number)
        if not tenant:
            return MessageTemplates.unauthorized_phone()

        phone_key = self.client.normalize_phone_key(from_number)
        self.store.set_tenant(phone_key, str(tenant.id))

        cmd = self.parser.parse(body)
        logger.info("WhatsApp inbound from %s: %s -> %s", phone_key, body, cmd.type)

        if cmd.type == CommandType.HELP:
            return MessageTemplates.help_text()

        if cmd.type == CommandType.STATUS:
            counts = self.workflow.count_by_status(session, tenant.id)
            auto = getattr(tenant, "whatsapp_auto_approve", False)
            return MessageTemplates.status(counts["pending"], auto)

        if cmd.type == CommandType.SUMMARY:
            return await self.build_daily_summary(session, tenant.id)

        if cmd.type == CommandType.AUTO_ON:
            tenant.whatsapp_auto_approve = True
            session.add(tenant)
            session.commit()
            return MessageTemplates.auto_approve_enabled(tenant.name)

        if cmd.type == CommandType.AUTO_OFF:
            tenant.whatsapp_auto_approve = False
            session.add(tenant)
            session.commit()
            return MessageTemplates.auto_approve_disabled(tenant.name)

        pending_items = self.store.get_pending(phone_key)
        if not pending_items and cmd.type in (
            CommandType.APPROVE,
            CommandType.REJECT,
            CommandType.APPROVE_ALL,
            CommandType.REJECT_ALL,
        ):
            pending_items = self._pending_from_db(session, tenant.id)

        if cmd.type == CommandType.APPROVE_ALL:
            return self._approve_all(session, tenant, pending_items, phone_key)

        if cmd.type == CommandType.REJECT_ALL:
            return self._reject_all(session, tenant, pending_items, phone_key)

        if cmd.type in (CommandType.APPROVE, CommandType.REJECT):
            index = cmd.index or 1
            return self._handle_single(
                session, tenant, pending_items, phone_key, cmd.type, index
            )

        return MessageTemplates.unknown_command()

    def _pending_from_db(
        self, session: Session, tenant_id: UUID
    ) -> list[dict[str, Any]]:
        recs = session.exec(
            select(Recommendation).where(
                Recommendation.tenant_id == tenant_id,
                Recommendation.status == "pending",
            )
        ).all()
        return [
            {
                "index": i,
                "recommendation_id": str(r.id),
                "product_name": "item",
            }
            for i, r in enumerate(recs, 1)
        ]

    def _handle_single(
        self,
        session: Session,
        tenant: Tenant,
        items: list[dict[str, Any]],
        phone_key: str,
        cmd_type: CommandType,
        index: int,
    ) -> str:
        if not items:
            return MessageTemplates.no_pending()

        item = next((x for x in items if x.get("index") == index), None)
        if not item and 0 < index <= len(items):
            item = items[index - 1]
        if not item:
            return f"Invalid item #{index}. Reply *STATUS* for pending count."

        rec_id = UUID(item["recommendation_id"])
        if cmd_type == CommandType.APPROVE:
            result = self.workflow.approve(session, rec_id, via="whatsapp")
        else:
            result = self.workflow.reject(session, rec_id, via="whatsapp")

        if not result.get("ok"):
            return f"Could not process: {result.get('error', 'unknown')}"

        self.store.remove_pending_index(phone_key, index)
        return result["message"]

    def _approve_all(
        self,
        session: Session,
        tenant: Tenant,
        items: list[dict[str, Any]],
        phone_key: str,
    ) -> str:
        if not items:
            return MessageTemplates.no_pending()
        lines = [f"Approved {len(items)} item(s):"]
        for item in items:
            rec_id = UUID(item["recommendation_id"])
            r = self.workflow.approve(session, rec_id, via="whatsapp")
            if r.get("ok"):
                lines.append(f"• {r.get('product_name')}")
        self.store.clear_pending(phone_key)
        return "\n".join(lines)

    def _reject_all(
        self,
        session: Session,
        tenant: Tenant,
        items: list[dict[str, Any]],
        phone_key: str,
    ) -> str:
        if not items:
            return MessageTemplates.no_pending()
        for item in items:
            self.workflow.reject(session, UUID(item["recommendation_id"]), via="whatsapp")
        self.store.clear_pending(phone_key)
        return f"Rejected {len(items)} pricing suggestion(s)."

    async def build_daily_summary(self, session: Session, tenant_id: UUID) -> str:
        tenant = session.get(Tenant, tenant_id)
        if not tenant:
            return "Store not found."

        counts = self.workflow.count_by_status(session, tenant_id)
        now = datetime.now(timezone.utc)
        date_label = now.strftime("%a %d %b %Y")

        weather_line = None
        event_line = None
        top_insight = "Review pending recommendations to capture demand."

        try:
            from backend.services.weather_intelligence.service import (
                weather_intelligence_service,
            )
            from backend.services.event_intelligence.service import (
                event_intelligence_service,
            )

            w = await weather_intelligence_service.get_intelligence_for_tenant(
                session, tenant_id, use_cache=True, persist_signal=False
            )
            c = w.current
            weather_line = f"{c.condition_label or c.condition.value}, {c.temperature_c:.0f}°C"
            if c.is_heavy_rain:
                weather_line += " — heavy rain playbook active"

            e = await event_intelligence_service.get_intelligence_for_tenant(
                session, tenant_id, use_cache=True, persist_signal=False
            )
            if e.events:
                top = e.events[0]
                event_line = f"{top.name} (impact {top.impact_score:.0f}/100)"
                top_insight = f"Top event: {top.name} — consider surge or bundle pricing."
        except Exception as exc:
            logger.warning("Summary signal fetch failed: %s", exc)

        return MessageTemplates.daily_summary(
            store_name=tenant.name,
            date_label=date_label,
            pending_count=counts["pending"],
            approved_count=counts["approved"],
            rejected_count=counts["rejected"],
            top_insight=top_insight,
            weather_line=weather_line,
            event_line=event_line,
            revenue_hint="Open dashboard for full analytics.",
        )

    async def send_daily_summaries(self, session: Session) -> dict[str, Any]:
        tenants = session.exec(
            select(Tenant).where(
                Tenant.whatsapp_enabled == True,  # noqa: E712
            )
        ).all()
        sent = 0
        for tenant in tenants:
            if not tenant.whatsapp_phone:
                continue
            body = await self.build_daily_summary(session, tenant.id)
            result = await self.client.send_message(tenant.whatsapp_phone, body)
            if result.get("ok"):
                sent += 1
        return {"ok": True, "tenants_notified": sent}


whatsapp_agent = WhatsAppBusinessAgent()
