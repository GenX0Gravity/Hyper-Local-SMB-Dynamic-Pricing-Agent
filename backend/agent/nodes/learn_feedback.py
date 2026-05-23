"""Node 5: Learn from historical owner feedback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session

from backend.agent.memory import AgentMemoryStore
from backend.agent.state import AgentPhase, PricingAgentState
from backend.agent.tools.feedback import load_feedback_memory, record_run_outcome
from backend.core.database import engine

logger = logging.getLogger(__name__)


def learn_feedback_node(state: PricingAgentState) -> dict:
    logger.info("Agent[%s]: learning from feedback", state.get("run_id"))
    memory = AgentMemoryStore()
    business_id = state["business_id"]

    with Session(engine) as session:
        feedback = load_feedback_memory(session, memory, business_id)

    signals = state.get("signals")
    sources_ok = getattr(signals, "sources_ok", []) if signals else []

    record_run_outcome(
        memory,
        business_id,
        state.get("run_id", "unknown"),
        {
            "recommendation_count": len(state.get("recommendations") or []),
            "signals_ok": sources_ok,
            "notification_sent": state.get("notification_sent", False),
            "errors": len(state.get("errors") or []),
        },
    )

    return {
        "phase": AgentPhase.COMPLETE,
        "feedback": feedback,
        "completed_at": datetime.now(timezone.utc),
    }
