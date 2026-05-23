"""Feedback learning tools — read/write agent memory."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlmodel import Session, select

from backend.agent.memory import AgentMemoryStore
from backend.agent.state import FeedbackSnapshot
from backend.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


def load_feedback_memory(
    session: Session,
    memory: AgentMemoryStore,
    business_id: UUID,
) -> FeedbackSnapshot:
    """Blend DB recommendation outcomes with Redis session memory."""
    approved = 0
    rejected = 0

    recs = session.exec(
        select(Recommendation).where(Recommendation.tenant_id == business_id)
    ).all()

    for rec in recs[-100:]:
        if rec.status == "approved":
            approved += 1
        elif rec.status == "rejected":
            rejected += 1

    cached = memory.get_feedback_profile(str(business_id))
    cap = float(cached.get("preferred_discount_cap_pct", 15.0))
    if rejected > approved * 2 and approved + rejected >= 5:
        cap = max(5.0, cap - 2.0)

    return FeedbackSnapshot(
        approved_count=approved,
        rejected_count=rejected,
        preferred_discount_cap_pct=cap,
    )


def record_run_outcome(
    memory: AgentMemoryStore,
    business_id: UUID,
    run_id: str,
    outcome: dict,
) -> None:
    memory.append_run_log(str(business_id), run_id, outcome)
    if outcome.get("owner_feedback"):
        profile = memory.get_feedback_profile(str(business_id))
        fb = outcome["owner_feedback"]
        if fb.get("rejected"):
            profile["preferred_discount_cap_pct"] = max(
                5.0, profile.get("preferred_discount_cap_pct", 15) - 1
            )
        memory.set_feedback_profile(str(business_id), profile)
