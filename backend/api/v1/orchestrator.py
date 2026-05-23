"""Orchestrator API: runs Weather -> Events -> Forecast -> Pricing -> WhatsApp"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.api.deps import get_current_tenant_id, get_db

from backend.services.weather_intelligence.service import weather_intelligence_service
from backend.services.event_intelligence.service import event_intelligence_service
from backend.forecasting.service import demand_forecasting_service
from backend.services.dynamic_pricing.service import dynamic_pricing_service
from backend.services.whatsapp_agent.notifier import RecommendationNotifier

router = APIRouter()


@router.post("/trigger")
async def trigger_full_workflow(tenant_id: UUID = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    """Trigger the end-to-end workflow and optionally send WhatsApp notifications."""
    # 1. Weather intelligence
    try:
        weather_report = await weather_intelligence_service.get_intelligence_for_tenant(db, tenant_id, use_cache=True, persist_signal=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Weather error: {exc}")

    # 2. Event intelligence
    try:
        event_report = await event_intelligence_service.get_intelligence_for_tenant(db, tenant_id, use_cache=True, persist_signal=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Event error: {exc}")

    # 3. Batch demand prediction
    try:
        batch_preds = await demand_forecasting_service.predict_batch(db, tenant_id)
    except FileNotFoundError:
        # If no model yet, retrain quickly (best-effort) then predict
        await demand_forecasting_service.retrain(db, tenant_id)
        batch_preds = await demand_forecasting_service.predict_batch(db, tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forecast error: {exc}")

    # 4. Pricing decision
    try:
        pricing_report = await dynamic_pricing_service.evaluate_tenant(db, tenant_id, demand_score=None, persist=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pricing error: {exc}")

    # 5. Send WhatsApp notifications (best-effort)
    try:
        notifier = RecommendationNotifier()
        notify_result = await notifier.send_recommendations(db, tenant_id, weather_context=None)
    except Exception:
        notify_result = {"ok": False}

    return {
        "weather": {"cache_hit": getattr(weather_report, "cache_hit", None)},
        "events": {"aggregate_impact_score": getattr(event_report, "aggregate_impact_score", None)},
        "predictions_count": len(batch_preds.predictions) if hasattr(batch_preds, "predictions") else None,
        "pricing_recommendations": len(pricing_report.recommendations) if hasattr(pricing_report, "recommendations") else None,
        "notify": notify_result,
    }
