"""Legacy WhatsApp facade — delegates to Twilio WhatsApp client."""

import logging

from backend.services.whatsapp_agent.twilio_client import twilio_client

logger = logging.getLogger(__name__)


class WhatsAppService:
    @staticmethod
    async def send_whatsapp_message(to_number: str, message_body: str) -> bool:
        result = await twilio_client.send_message(to_number, message_body)
        return bool(result.get("ok"))


whatsapp_service = WhatsAppService()
