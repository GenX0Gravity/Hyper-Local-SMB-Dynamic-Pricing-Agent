"""
Legacy event service — delegates to Event Intelligence Engine for backward compatibility.
"""

import logging
from typing import Any, Dict, List

from backend.services.event_intelligence.service import event_intelligence_service

logger = logging.getLogger(__name__)


class EventService:
    @staticmethod
    async def get_upcoming_events(
        latitude: float, longitude: float, radius_km: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Fetches classified local events with impact scores.
        Backward-compatible list[dict] for agents, Celery, and forecasting.
        """
        report = await event_intelligence_service.get_intelligence(
            latitude=latitude,
            longitude=longitude,
            use_cache=True,
            radius_km=radius_km,
        )
        return event_intelligence_service.to_legacy_event_list(report)


event_service = EventService()
