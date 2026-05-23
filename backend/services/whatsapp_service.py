import httpx
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    @staticmethod
    async def send_whatsapp_message(to_number: str, message_body: str) -> bool:
        """
        Dispatches a WhatsApp message using Twilio's API.
        If Twilio integration is disabled or keys are empty, mock logs are output.
        """
        formatted_to = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number

        if not settings.TWILIO_ENABLED or not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.info(
                f"[MOCK WHATSAPP SEND] to: {formatted_to} | from: {settings.TWILIO_WHATSAPP_FROM} | message: {message_body}"
            )
            return True
            
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        
        data = {
            "From": settings.TWILIO_WHATSAPP_FROM,
            "To": formatted_to,
            "Body": message_body
        }
        
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, auth=auth, timeout=10.0)
                if response.status_code in [200, 201]:
                    logger.info(f"WhatsApp notification sent successfully to {formatted_to}")
                    return True
                else:
                    logger.error(f"Twilio WhatsApp dispatch failed: {response.text}")
            except Exception as e:
                logger.error(f"Error communicating with Twilio WhatsApp API: {str(e)}")
                
        return False

whatsapp_service = WhatsAppService()
