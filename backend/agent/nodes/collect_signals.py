"""Node 1: Collect signals from all external sources."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel import Session

from backend.agent.memory import AgentMemoryStore
from backend.agent.recovery import build_error
from backend.agent.state import AgentPhase, AgentError, PricingAgentState, SignalBundle
from backend.agent.tools.signals import (
    fetch_events,
    fetch_footfall,
    fetch_news,
    fetch_sales_history,
    fetch_weather,
)
from backend.core.database import engine

logger = logging.getLogger(__name__)


async def _collect_async(state: PricingAgentState) -> tuple[SignalBundle, list[AgentError]]:
    lat = state["latitude"]
    lon = state["longitude"]
    business_id = state["business_id"]
    memory = AgentMemoryStore()
    errors: list[AgentError] = []

    if state.get("use_cached_signals"):
        cached = memory.get_cached_signals(str(business_id), str(state["location_id"]))
        if cached:
            return SignalBundle(**cached), errors

    weather_r, footfall_r, news_r, events_r = await asyncio.gather(
        fetch_weather(lat, lon),
        fetch_footfall(lat, lon),
        fetch_news(),
        fetch_events(lat, lon),
        return_exceptions=True,
    )

    with Session(engine) as session:
        sales_r = fetch_sales_history(session, business_id)

    bundle = SignalBundle(collected_at=datetime.now(timezone.utc))

    def apply(result, name: str, setter) -> None:
        if isinstance(result, Exception):
            bundle.sources_failed.append(name)
            errors.append(build_error("collect_signals", str(result), tool=name))
            return
        if not result.get("ok"):
            bundle.sources_failed.append(name)
            errors.append(
                build_error(
                    "collect_signals",
                    result.get("error", "unknown"),
                    tool=name,
                )
            )
            return
        bundle.sources_ok.append(name)
        setter(result["data"])

    apply(weather_r, "weather", lambda d: setattr(bundle, "weather", d))
    apply(footfall_r, "footfall", lambda d: setattr(bundle, "footfall", d))
    apply(news_r, "news", lambda d: setattr(bundle, "news", d))
    apply(events_r, "events", lambda d: setattr(bundle, "events", d))
    apply(sales_r, "sales", lambda d: setattr(bundle, "sales_summary", d))

    memory.cache_signals(
        str(business_id),
        str(state["location_id"]),
        bundle.model_dump(mode="json"),
    )
    return bundle, errors


def collect_signals_node(state: PricingAgentState) -> dict:
    logger.info("Agent[%s]: collecting signals", state.get("run_id"))
    prior_errors: list[AgentError] = list(state.get("errors") or [])

    try:
        bundle, new_errors = asyncio.run(_collect_async(state))
    except Exception as exc:
        logger.exception("Signal collection crashed")
        bundle = SignalBundle()
        new_errors = [build_error("collect_signals", str(exc), recoverable=True)]

    return {
        "phase": AgentPhase.COLLECT_SIGNALS,
        "signals": bundle,
        "errors": prior_errors + new_errors,
    }
