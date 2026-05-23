"""Node 4: Notify business owner."""

from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session

from backend.agent.state import AgentPhase, PricingAgentState
from backend.agent.tools.actions import persist_recommendations, send_owner_notification
from backend.core.database import engine

logger = logging.getLogger(__name__)


def notify_owner_node(state: PricingAgentState) -> dict:
    logger.info("Agent[%s]: notifying owner", state.get("run_id"))
    recs = state.get("recommendations") or []
    if not recs:
        return {
            "phase": AgentPhase.NOTIFY_OWNER,
            "notification_sent": False,
            "notification_body": None,
        }

    with Session(engine) as session:
        persist_recommendations(
            session,
            state["business_id"],
            recs,
            state.get("product_catalog") or [],
        )

    result = asyncio.run(
        send_owner_notification(
            state.get("whatsapp_phone"),
            state.get("business_name", "your store"),
            recs,
            state.get("whatsapp_enabled", False),
        )
    )

    return {
        "phase": AgentPhase.NOTIFY_OWNER,
        "notification_sent": result.get("ok", False),
        "notification_body": result.get("body"),
    }
