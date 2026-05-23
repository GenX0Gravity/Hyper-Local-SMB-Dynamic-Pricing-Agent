from celery import Celery
from celery.schedules import crontab
from backend.core.config import settings

celery_app = Celery(
    "pricepulse_workers",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_CACHE_URL,
    include=["backend.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat scheduler configurations
celery_app.conf.beat_schedule = {
    "refresh-all-demand-signals-hourly": {
        "task": "backend.workers.tasks.periodic_demand_signals_refresh",
        "schedule": crontab(minute=0), # Every hour
    },
    "retrain-forecast-models-weekly": {
        "task": "backend.workers.tasks.periodic_forecast_retrain",
        "schedule": crontab(minute=30, hour=3, day_of_week=1),  # Monday 03:30 UTC
    },
    "whatsapp-daily-summary": {
        "task": "backend.workers.tasks.send_whatsapp_daily_summaries",
        "schedule": crontab(
            minute=0,
            hour=settings.WHATSAPP_DAILY_SUMMARY_HOUR_UTC,
        ),
    },
    "analytics-weekly-reports": {
        "task": "backend.workers.tasks.generate_weekly_analytics_reports",
        "schedule": crontab(minute=15, hour=6, day_of_week=1),
    },
    "analytics-monthly-reports": {
        "task": "backend.workers.tasks.generate_monthly_analytics_reports",
        "schedule": crontab(minute=30, hour=6, day_of_month=1),
    },
}
