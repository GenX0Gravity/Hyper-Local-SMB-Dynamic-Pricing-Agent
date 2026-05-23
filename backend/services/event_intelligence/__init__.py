"""Event Intelligence Engine — multi-source monitoring and impact scoring."""

from backend.services.event_intelligence.service import event_intelligence_service
from backend.services.event_intelligence.schemas import (
    EventCategory,
    EventIntelligenceReport,
    ClassifiedEvent,
)

__all__ = [
    "event_intelligence_service",
    "EventCategory",
    "EventIntelligenceReport",
    "ClassifiedEvent",
]
