"""
LangGraph workflow for the autonomous PricePulse pricing agent.

Flow:
  START → load_context → collect_signals → predict_demand → decide_pricing
        → notify_owner → learn_feedback → END

Error recovery edges:
  collect_signals → retry_collect (loop) | use_cache → predict_demand
  predict_demand → degraded_decide (skip LLM, rules-only) on repeated failure
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph
from sqlmodel import Session, select

from backend.agent.memory import AgentMemoryStore
from backend.agent.nodes import (
    collect_signals_node,
    decide_pricing_node,
    learn_feedback_node,
    notify_owner_node,
    predict_demand_node,
)
from backend.agent.recovery import (
    increment_retry,
    route_after_decide,
    route_after_predict,
    route_after_signals,
)
from backend.agent.state import AgentPhase, FeedbackSnapshot, PricingAgentState
from backend.agent.tools.feedback import load_feedback_memory
from backend.core.config import settings
from backend.core.database import engine
from backend.models.product import Product
from backend.models.tenant import Tenant

logger = logging.getLogger(__name__)


def load_context_node(state: PricingAgentState) -> dict:
    """Hydrate tenant catalog and feedback profile before signal collection."""
    business_id = state["business_id"]
    memory = AgentMemoryStore()

    with Session(engine) as session:
        tenant = session.exec(
            select(Tenant).where(Tenant.id == business_id)
        ).first()
        if not tenant:
            raise ValueError(f"Tenant/business {business_id} not found")

        products = session.exec(
            select(Product).where(Product.tenant_id == business_id)
        ).all()
        feedback = load_feedback_memory(session, memory, business_id)

    catalog = [
        {
            "id": str(p.id),
            "name": p.name,
            "category": p.category,
            "current_price": p.current_price,
            "base_price": p.base_price,
            "min_price": p.min_price,
            "max_price": p.max_price,
            "stock_qty": p.stock_qty,
        }
        for p in products
    ]

    return {
        "business_name": tenant.name,
        "latitude": tenant.latitude,
        "longitude": tenant.longitude,
        "timezone": tenant.timezone,
        "currency": tenant.currency,
        "whatsapp_phone": tenant.whatsapp_phone,
        "whatsapp_enabled": tenant.whatsapp_enabled,
        "product_catalog": catalog,
        "feedback": feedback,
        "location_id": state.get("location_id") or business_id,
        "max_retries": settings.AGENT_MAX_RETRIES,
        "retry_count": state.get("retry_count", 0),
        "phase": AgentPhase.INIT,
    }


def retry_collect_node(state: PricingAgentState) -> dict:
    updates = increment_retry(state)
    updates["use_cached_signals"] = False
    return updates


def use_cache_node(state: PricingAgentState) -> dict:
    return {"use_cached_signals": True, **increment_retry(state)}


def degraded_decide_node(state: PricingAgentState) -> dict:
    """Minimal recommendations when signals/forecast pipeline fails."""
    from backend.agent.state import PricingRecommendation, RecommendationType

    recs = [
        PricingRecommendation(
            recommendation_type=RecommendationType.DISCOUNT,
            title="Safe default — slow day promo",
            description="Degraded mode: apply up to 10% off slow movers.",
            adjustment_pct=-10.0,
            priority=30,
            metadata={"degraded": True},
        )
    ]
    return {"recommendations": recs, "phase": AgentPhase.DECIDE_PRICING}


def _route_signals(state: PricingAgentState) -> str:
    route = route_after_signals(state)
    mapping = {
        "continue": "predict_demand",
        "retry_collect": "retry_collect",
        "use_cache": "use_cache",
        "degraded_decide": "degraded_decide",
        "abort": "learn_feedback",
    }
    return mapping.get(route, "predict_demand")


def _route_predict(state: PricingAgentState) -> str:
    route = route_after_predict(state)
    if route == "degraded_decide":
        return "degraded_decide"
    return "decide_pricing"


def _route_decide(state: PricingAgentState) -> str:
    route = route_after_decide(state)
    if route == "abort":
        return "learn_feedback"
    return "notify_owner"


def build_pricing_agent_graph():
    graph = StateGraph(PricingAgentState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("collect_signals", collect_signals_node)
    graph.add_node("retry_collect", retry_collect_node)
    graph.add_node("use_cache", use_cache_node)
    graph.add_node("predict_demand", predict_demand_node)
    graph.add_node("decide_pricing", decide_pricing_node)
    graph.add_node("degraded_decide", degraded_decide_node)
    graph.add_node("notify_owner", notify_owner_node)
    graph.add_node("learn_feedback", learn_feedback_node)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "collect_signals")

    graph.add_conditional_edges("collect_signals", _route_signals)
    graph.add_edge("retry_collect", "collect_signals")
    graph.add_edge("use_cache", "collect_signals")

    graph.add_conditional_edges("predict_demand", _route_predict)
    graph.add_edge("degraded_decide", "notify_owner")
    graph.add_conditional_edges("decide_pricing", _route_decide)
    graph.add_edge("notify_owner", "learn_feedback")
    graph.add_edge("learn_feedback", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_pricing_agent_graph()
    return _compiled_graph


def run_pricing_agent(
    business_id: UUID,
    location_id: UUID | None = None,
    triggered_by: str = "celery",
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    initial: PricingAgentState = {
        "run_id": run_id,
        "business_id": business_id,
        "location_id": location_id or business_id,
        "triggered_by": triggered_by,
        "phase": AgentPhase.INIT,
        "recommendations": [],
        "errors": [],
        "retry_count": 0,
        "use_cached_signals": False,
        "notification_sent": False,
    }

    logger.info("Starting pricing agent run %s for business %s", run_id, business_id)
    result = get_graph().invoke(initial)
    return {
        "run_id": run_id,
        "phase": result.get("phase"),
        "recommendation_count": len(result.get("recommendations") or []),
        "notification_sent": result.get("notification_sent"),
        "errors": [e.model_dump() if hasattr(e, "model_dump") else e for e in result.get("errors") or []],
        "completed_at": result.get("completed_at"),
    }
