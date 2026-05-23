"""Redis session store — pending approvals mapped to WhatsApp numbers."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from backend.core.config import settings

logger = logging.getLogger(__name__)

PENDING_KEY = "whatsapp:pending:{phone}"
TENANT_KEY = "whatsapp:tenant:{phone}"


class WhatsAppSessionStore:
    def __init__(self, redis_url: str | None = None):
        self._redis: redis.Redis | None = None
        url = redis_url or settings.REDIS_CACHE_URL
        try:
            client = redis.from_url(url, decode_responses=True)
            client.ping()
            self._redis = client
        except Exception as exc:
            logger.warning("WhatsApp session store unavailable: %s", exc)

    def _pending_key(self, phone_key: str) -> str:
        return PENDING_KEY.format(phone=phone_key)

    def _tenant_key(self, phone_key: str) -> str:
        return TENANT_KEY.format(phone=phone_key)

    def set_tenant(self, phone_key: str, tenant_id: str, ttl: int | None = None) -> None:
        if not self._redis:
            return
        ttl = ttl or settings.WHATSAPP_SESSION_TTL_SECONDS
        self._redis.setex(self._tenant_key(phone_key), ttl, tenant_id)

    def get_tenant(self, phone_key: str) -> Optional[str]:
        if not self._redis:
            return None
        return self._redis.get(self._tenant_key(phone_key))

    def set_pending(self, phone_key: str, items: list[dict[str, Any]]) -> None:
        if not self._redis:
            return
        self._redis.setex(
            self._pending_key(phone_key),
            settings.WHATSAPP_SESSION_TTL_SECONDS,
            json.dumps(items, default=str),
        )

    def get_pending(self, phone_key: str) -> list[dict[str, Any]]:
        if not self._redis:
            return []
        raw = self._redis.get(self._pending_key(phone_key))
        if not raw:
            return []
        return json.loads(raw)

    def remove_pending_index(self, phone_key: str, index: int) -> list[dict[str, Any]]:
        items = self.get_pending(phone_key)
        if not items:
            return []
        idx = index - 1
        if 0 <= idx < len(items):
            items.pop(idx)
        self.set_pending(phone_key, items)
        return items

    def clear_pending(self, phone_key: str) -> None:
        if not self._redis:
            return
        self._redis.delete(self._pending_key(phone_key))
