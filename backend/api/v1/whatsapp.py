"""WhatsApp Business Agent API — webhooks and notification triggers."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.api.deps import get_current_tenant_id, get_db
from backend.core.config import settings
from backend.models.tenant import Tenant
from backend.services.whatsapp_agent.agent import whatsapp_agent
from backend.services.whatsapp_agent.notifier import RecommendationNotifier
from backend.services.whatsapp_agent.twilio_client import twilio_client

logger = logging.getLogger(__name__)
router = APIRouter()


class WhatsAppSettingsResponse(BaseModel):
    whatsapp_phone: Optional[str]
    whatsapp_enabled: bool
    whatsapp_auto_approve: bool
    webhook_url: str


class WhatsAppSettingsUpdate(BaseModel):
    whatsapp_enabled: Optional[bool] = None
    whatsapp_auto_approve: Optional[bool] = None
    whatsapp_phone: Optional[str] = None


class NotifyRecommendationsRequest(BaseModel):
    include_weather_context: bool = True


@router.get("/settings", response_model=WhatsAppSettingsResponse)
def get_whatsapp_settings(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    base = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else "http://localhost:8000"
    webhook = f"{base.rstrip('/')}{settings.API_V1_STR}/whatsapp/webhook/inbound"
    return WhatsAppSettingsResponse(
        whatsapp_phone=tenant.whatsapp_phone,
        whatsapp_enabled=tenant.whatsapp_enabled,
        whatsapp_auto_approve=getattr(tenant, "whatsapp_auto_approve", False),
        webhook_url=webhook,
    )


@router.patch("/settings", response_model=WhatsAppSettingsResponse)
def update_whatsapp_settings(
    payload: WhatsAppSettingsUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return get_whatsapp_settings(tenant_id=tenant_id, db=db)


@router.post("/webhook/inbound")
async def twilio_inbound_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Twilio WhatsApp inbound webhook.
    Configure in Twilio Console → Messaging → WhatsApp Sandbox →
    "When a message comes in" → POST this URL.
    """
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    signature = request.headers.get("X-Twilio-Signature")
    if settings.TWILIO_WEBHOOK_BASE_URL:
        url = settings.TWILIO_WEBHOOK_BASE_URL.rstrip("/") + str(request.url.path)
        if request.url.query:
            url = f"{url}?{request.url.query}"
    else:
        url = str(request.url)

    if settings.TWILIO_AUTH_TOKEN and not twilio_client.validate_webhook_signature(
        url, params, signature
    ):
        logger.warning("Invalid Twilio webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    from_number = params.get("From", "")
    body = params.get("Body", "")

    reply = await whatsapp_agent.handle_inbound(db, from_number, body)
    twiml = twilio_client.twiml_message(reply)
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/status")
async def twilio_status_webhook(request: Request):
    """Optional delivery status callback."""
    form = await request.form()
    params = dict(form)
    logger.info(
        "WhatsApp status: sid=%s status=%s",
        params.get("MessageSid"),
        params.get("MessageStatus"),
    )
    return {"ok": True}


@router.post("/notify/recommendations")
async def notify_pricing_recommendations(
    body: NotifyRecommendationsRequest | None = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Send pending pricing recommendations via WhatsApp."""
    req = body or NotifyRecommendationsRequest()
    weather_ctx = None
    if req.include_weather_context:
        try:
            from backend.services.weather_intelligence.service import (
                weather_intelligence_service,
            )

            tenant = db.get(Tenant, tenant_id)
            report = await weather_intelligence_service.get_intelligence_for_tenant(
                db, tenant_id, use_cache=True, persist_signal=False
            )
            c = report.current
            weather_ctx = {
                "store_name": tenant.name if tenant else "Store",
                "condition": c.condition_label,
                "is_heavy_rain": c.is_heavy_rain,
                "heavy_rain_time": "at 4 PM"
                if report.forecast and report.forecast.heavy_rain_within_hours
                else "soon",
                "suggested_discount": 20.0,
                "category": "tea & hot beverages",
            }
        except Exception as exc:
            logger.warning("Weather context for WhatsApp skipped: %s", exc)

    notifier = RecommendationNotifier()
    return await notifier.send_recommendations(
        db, tenant_id, weather_context=weather_ctx
    )


@router.post("/notify/daily-summary")
async def notify_daily_summary(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Send daily summary report to store WhatsApp."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant or not tenant.whatsapp_enabled or not tenant.whatsapp_phone:
        raise HTTPException(status_code=400, detail="WhatsApp not enabled for tenant")

    body = await whatsapp_agent.build_daily_summary(db, tenant_id)
    result = await twilio_client.send_message(tenant.whatsapp_phone, body)
    return {"ok": result.get("ok"), "message_preview": body[:200]}


@router.post("/notify/weather-alert")
async def notify_weather_alert(
    condition: str = Query("Heavy rain"),
    time_label: str = Query("at 4 PM"),
    discount_pct: float = Query(20.0, ge=0, le=30),
    category: str = Query("tea & hot beverages"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Send sample-style weather pricing alert."""
    notifier = RecommendationNotifier()
    return await notifier.send_weather_alert(
        db,
        tenant_id,
        condition=condition,
        time_label=time_label,
        discount_pct=discount_pct,
        category=category,
    )
