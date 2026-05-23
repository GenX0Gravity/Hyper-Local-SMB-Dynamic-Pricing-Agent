"""Twilio WhatsApp client — send messages, validate webhooks, TwiML replies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any
import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class TwilioWhatsAppClient:
    API_BASE = "https://api.twilio.com/2010-04-01"

    def format_whatsapp_number(self, number: str) -> str:
        if number.startswith("whatsapp:"):
            return number
        cleaned = number.strip()
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned.lstrip('+')}"
        return f"whatsapp:{cleaned}"

    def normalize_phone_key(self, number: str) -> str:
        """Digits-only key for Redis / tenant lookup."""
        raw = number.replace("whatsapp:", "").replace("+", "").strip()
        return raw

    async def send_message(self, to_number: str, body: str) -> dict[str, Any]:
        to_addr = self.format_whatsapp_number(to_number)
        from_addr = settings.TWILIO_WHATSAPP_FROM
        if not from_addr.startswith("whatsapp:"):
            from_addr = f"whatsapp:{from_addr}"

        if (
            not settings.TWILIO_ENABLED
            or not settings.TWILIO_ACCOUNT_SID
            or not settings.TWILIO_AUTH_TOKEN
        ):
            logger.info("[MOCK WHATSAPP] to=%s body=%s", to_addr, body[:120])
            return {"ok": True, "mock": True, "sid": "mock-sid"}

        url = f"{self.API_BASE}/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        data = {"From": from_addr, "To": to_addr, "Body": body}
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, auth=auth, timeout=15.0)
                if response.status_code in (200, 201):
                    payload = response.json()
                    return {"ok": True, "sid": payload.get("sid"), "status": payload.get("status")}
                logger.error("Twilio send failed: %s", response.text)
                return {"ok": False, "error": response.text}
            except Exception as exc:
                logger.exception("Twilio send error")
                return {"ok": False, "error": str(exc)}

    def twiml_message(self, body: str) -> str:
        """TwiML XML for synchronous webhook replies."""
        escaped = (
            body.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escaped}</Message></Response>'

    def validate_webhook_signature(
        self,
        url: str,
        params: dict[str, str],
        signature: str | None,
    ) -> bool:
        """
        Validate X-Twilio-Signature per Twilio docs.
        Skip validation when auth token unset (local dev).
        """
        if not settings.TWILIO_AUTH_TOKEN:
            return True
        if not signature:
            return False

        sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        data = url + sorted_params
        digest = hmac.new(
            settings.TWILIO_AUTH_TOKEN.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        computed = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(computed, signature)


twilio_client = TwilioWhatsAppClient()
