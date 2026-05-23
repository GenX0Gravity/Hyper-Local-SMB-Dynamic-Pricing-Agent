"""
Agent memory architecture — three tiers:

1. Working memory (LangGraph state) — single run, in-process
2. Session memory (Redis) — signal cache, run logs, feedback profile TTL
3. Long-term memory (PostgreSQL) — pricing_actions, audit_logs, sales_history
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from backend.core.config import settings

logger = logging.getLogger(__name__)

FEEDBACK_KEY = "agent:feedback:{business_id}"
SIGNALS_KEY = "agent:signals:{business_id}:{location_id}"
RUN_LOG_KEY = "agent:runs:{business_id}"


class AgentMemoryStore:
    def __init__(self, redis_url: Optional[str] = None):
        url = redis_url or settings.REDIS_CACHE_URL
        try:
            self._redis = redis.from_url(url, decode_responses=True)
            self._redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable for agent memory: %s", exc)
            self._redis = None

    def _key(self, template: str, **kwargs: str) -> str:
        return template.format(**kwargs)

    # --- Session: signal cache ---

    def cache_signals(
        self, business_id: str, location_id: str, payload: dict[str, Any]
    ) -> None:
        if not self._redis:
            return
        key = self._key(SIGNALS_KEY, business_id=business_id, location_id=location_id)
        data = json.dumps(
            {"cached_at": datetime.now(timezone.utc).isoformat(), "signals": payload}
        )
        self._redis.setex(key, settings.AGENT_SIGNAL_CACHE_TTL_SECONDS, data)

    def get_cached_signals(
        self, business_id: str, location_id: str
    ) -> Optional[dict[str, Any]]:
        if not self._redis:
            return None
        key = self._key(SIGNALS_KEY, business_id=business_id, location_id=location_id)
        raw = self._redis.get(key)
        if not raw:
            return None
        return json.loads(raw).get("signals")

    # --- Session: feedback profile ---

    def get_feedback_profile(self, business_id: str) -> dict[str, Any]:
        if not self._redis:
            return {"preferred_discount_cap_pct": 15.0}
        key = self._key(FEEDBACK_KEY, business_id=business_id)
        raw = self._redis.get(key)
        if raw:
            return json.loads(raw)
        return {"preferred_discount_cap_pct": 15.0, "runs": 0}

    def set_feedback_profile(self, business_id: str, profile: dict[str, Any]) -> None:
        if not self._redis:
            return
        key = self._key(FEEDBACK_KEY, business_id=business_id)
        self._redis.set(key, json.dumps(profile))

    # --- Session: run history (last N runs) ---

    def append_run_log(
        self, business_id: str, run_id: str, outcome: dict[str, Any]
    ) -> None:
        if not self._redis:
            return
        key = self._key(RUN_LOG_KEY, business_id=business_id)
        entry = json.dumps(
            {
                "run_id": run_id,
                "at": datetime.now(timezone.utc).isoformat(),
                **outcome,
            }
        )
        pipe = self._redis.pipeline()
        pipe.lpush(key, entry)
        pipe.ltrim(key, 0, 99)
        pipe.execute()

    def recent_runs(self, business_id: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self._redis:
            return []
        key = self._key(RUN_LOG_KEY, business_id=business_id)
        items = self._redis.lrange(key, 0, limit - 1)
        return [json.loads(i) for i in items]
