"""
Error recovery flow for the pricing agent.

Strategies:
  - Per-tool soft fail (signals partial OK)
  - Retry with cached signals when collection fails
  - Circuit breaker after max_retries
  - Degraded mode: rules-only recommendations
"""

from __future__ import annotations

from typing import Literal

from backend.agent.state import AgentError, AgentPhase, PricingAgentState, SignalBundle


RecoveryRoute = Literal[
    "continue",
    "retry_collect",
    "use_cache",
    "degraded_decide",
    "abort",
]


def should_abort(state: PricingAgentState) -> bool:
    return state.get("retry_count", 0) >= state.get("max_retries", 3)


def route_after_signals(state: PricingAgentState) -> RecoveryRoute:
    signals: SignalBundle = state.get("signals") or SignalBundle()
    errors = state.get("errors") or []

    if signals.sources_ok:
        return "continue"

    if state.get("use_cached_signals"):
        return "continue"

    if should_abort(state):
        if signals.sources_failed and not signals.sources_ok:
            return "abort"
        return "degraded_decide"

    if errors and any(e.recoverable for e in errors if e.node == "collect_signals"):
        return "retry_collect"

    return "use_cache"


def route_after_predict(state: PricingAgentState) -> RecoveryRoute:
    if state.get("forecasts"):
        return "continue"
    if should_abort(state):
        return "degraded_decide"
    return "continue"


def route_after_decide(state: PricingAgentState) -> RecoveryRoute:
    recs = state.get("recommendations") or []
    if recs:
        return "continue"
    if should_abort(state):
        return "abort"
    return "continue"


def increment_retry(state: PricingAgentState) -> dict:
    return {"retry_count": state.get("retry_count", 0) + 1}


def build_error(
    node: str,
    message: str,
    tool: str | None = None,
    recoverable: bool = True,
    attempt: int = 1,
) -> AgentError:
    return AgentError(
        node=node,
        tool=tool,
        message=message,
        recoverable=recoverable,
        attempt=attempt,
    )


def phase_on_abort() -> AgentPhase:
    return AgentPhase.FAILED
