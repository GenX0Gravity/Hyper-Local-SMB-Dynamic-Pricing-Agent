import asyncio
import logging
from uuid import UUID
from sqlmodel import Session, select
from backend.workers.celery_app import celery_app
from backend.core.database import engine
from backend.models.tenant import Tenant
from backend.models.signal import DemandSignal
from backend.services.weather_intelligence.service import weather_intelligence_service
from backend.services.event_intelligence.service import event_intelligence_service
from backend.services.pricing_engine import PricingEngine
from backend.services.whatsapp_agent.notifier import RecommendationNotifier
from backend.agent.graph import run_pricing_agent
from backend.forecasting.service import demand_forecasting_service

logger = logging.getLogger(__name__)

# Helper to run async code inside synchronous Celery worker tasks
def run_async(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running, run task in the same loop
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return asyncio.run(coro)

@celery_app.task
def periodic_demand_signals_refresh():
    """
    Periodic task triggered by Celery Beat scheduler.
    Finds all active tenants and enqueues worker evaluation jobs for each store.
    """
    logger.info("Starting periodic check for all tenant demand signals...")
    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            sync_store_signals.delay(str(tenant.id))
    logger.info("Enqueued signal synchronization tasks for all tenants.")

@celery_app.task
def sync_store_signals(tenant_id_str: str):
    """
    Scrapes weather/event data for store location, runs engine rules audits,
    and updates pricing suggestions.
    """
    tenant_id = UUID(tenant_id_str)
    logger.info(f"Synchronizing demand signals for store tenant: {tenant_id}...")
    
    with Session(engine) as session:
        tenant = session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found in database. Skipping.")
            return

        weather_report = run_async(
            weather_intelligence_service.get_intelligence_for_tenant(
                session, tenant_id, use_cache=False, persist_signal=True
            )
        )
        weather_info = weather_intelligence_service.to_legacy_weather_dict(weather_report)
        event_report = run_async(
            event_intelligence_service.get_intelligence_for_tenant(
                session, tenant_id, use_cache=False, persist_signal=True
            )
        )
        events_info = event_intelligence_service.to_legacy_event_list(event_report)

        db_weather_signal = session.exec(
            select(DemandSignal)
            .where(
                DemandSignal.tenant_id == tenant_id,
                DemandSignal.signal_type == "weather",
            )
            .order_by(DemandSignal.recorded_at.desc())  # type: ignore
        ).first()

        db_event_signals = session.exec(
            select(DemandSignal)
            .where(
                DemandSignal.tenant_id == tenant_id,
                DemandSignal.signal_type == "event",
            )
            .order_by(DemandSignal.recorded_at.desc())  # type: ignore
        ).all()[: len(events_info)]
        
        # Run pricing engine rules evaluation
        active_signals = [s for s in ([db_weather_signal] + list(db_event_signals)) if s]
        recs = PricingEngine.evaluate_rules(session, tenant_id, active_signals)
        
        # Dispatch notifications if rules evaluated to suggestions
        if recs and tenant.whatsapp_enabled:
            weather_ctx = {
                "store_name": tenant.name,
                "condition": weather_info.get("condition"),
                "is_heavy_rain": weather_info.get("is_heavy_rain"),
                "heavy_rain_time": "at 4 PM",
                "suggested_discount": 20.0,
                "category": "tea & hot beverages",
            }
            run_async(
                RecommendationNotifier().send_recommendations(
                    session, tenant_id, weather_context=weather_ctx
                )
            )

        logger.info(f"Signal sync and pricing audit completed for store tenant: {tenant_id}.")


@celery_app.task
def run_autonomous_pricing_agent(tenant_id_str: str):
    """
    LangGraph autonomous pricing agent: signals → demand → decide → notify → learn.
    """
    tenant_id = UUID(tenant_id_str)
    logger.info("Running LangGraph pricing agent for tenant %s", tenant_id)
    try:
        result = run_pricing_agent(business_id=tenant_id, triggered_by="celery")
        logger.info("Pricing agent finished: %s", result)
        return result
    except Exception as exc:
        logger.exception("Pricing agent failed for tenant %s: %s", tenant_id, exc)
        raise


@celery_app.task
def retrain_forecast_model(tenant_id_str: str, lookback_days: int = 90):
    """Celery task: XGBoost retraining pipeline for one tenant."""
    tenant_id = UUID(tenant_id_str)
    with Session(engine) as session:
        result = demand_forecasting_service.retrain(
            session, tenant_id, lookback_days=lookback_days
        )
    logger.info("Forecast retrain complete for %s: v%s", tenant_id, result.model_version)
    return result.model_dump()


@celery_app.task
def periodic_forecast_retrain():
    """Enqueue retraining for all tenants (weekly beat schedule)."""
    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            retrain_forecast_model.delay(str(tenant.id))


@celery_app.task
def generate_weekly_analytics_reports():
    """Persist weekly analytics snapshots for all tenants."""
    from backend.services.analytics.service import analytics_service

    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            analytics_service.generate_and_persist_period(
                session, tenant.id, "weekly"
            )
    logger.info("Weekly analytics reports generated.")


@celery_app.task
def generate_monthly_analytics_reports():
    """Persist monthly analytics snapshots for all tenants."""
    from backend.services.analytics.service import analytics_service

    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            analytics_service.generate_and_persist_period(
                session, tenant.id, "monthly"
            )
    logger.info("Monthly analytics reports generated.")


@celery_app.task
def send_whatsapp_daily_summaries():
    """Send daily summary WhatsApp messages to all enabled tenants."""
    from backend.services.whatsapp_agent.agent import whatsapp_agent

    logger.info("Sending WhatsApp daily summaries...")
    with Session(engine) as session:
        result = run_async(whatsapp_agent.send_daily_summaries(session))
    logger.info("Daily summaries sent: %s", result)
    return result


@celery_app.task
def periodic_pricing_agent_run():
    """Enqueue LangGraph agent for every active tenant."""
    with Session(engine) as session:
        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            run_autonomous_pricing_agent.delay(str(tenant.id))
