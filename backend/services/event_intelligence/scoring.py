"""Event Impact Scoring Model — composite 0–100 Event Impact Score."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from backend.core.config import settings
from backend.services.event_intelligence.schemas import (
    ClassifiedEvent,
    EventCategory,
    RawEventRecord,
)
from backend.services.event_intelligence.classifier import EventClassifier


class EventImpactScorer:
    """
    Computes per-event and aggregate Event Impact Scores.

    Formula (weighted components, normalized 0–100):
      impact = category_weight × attendance_factor × proximity_factor
               × urgency_factor × trend_boost × sentiment_modifier
    """

    CATEGORY_WEIGHTS: dict[EventCategory, float] = {
        EventCategory.IPL_MATCH: 0.95,
        EventCategory.FOOTBALL_MATCH: 0.90,
        EventCategory.DURGA_PUJA: 0.88,
        EventCategory.COLLEGE_FESTIVAL: 0.72,
        EventCategory.PUBLIC_HOLIDAY: 0.68,
        EventCategory.LOCAL_EVENT: 0.55,
        EventCategory.UNKNOWN: 0.40,
    }

    def __init__(self, classifier: EventClassifier | None = None):
        self.classifier = classifier or EventClassifier()

    def score_raw(
        self,
        record: RawEventRecord,
        category: EventCategory,
        now: Optional[datetime] = None,
    ) -> tuple[float, dict[str, float], Optional[float]]:
        now = now or datetime.now(timezone.utc)
        factors: dict[str, float] = {}

        cat_weight = self.CATEGORY_WEIGHTS.get(category, 0.5)
        factors["category_weight"] = cat_weight

        attendance = max(record.attendance_est, 0)
        # Log-scaled attendance: 500 → ~0.35, 5000 → ~0.55, 50000 → ~0.75
        attendance_factor = min(
            1.0,
            math.log10(max(attendance, 1)) / math.log10(settings.EVENT_ATTENDANCE_CAP),
        )
        factors["attendance_factor"] = round(attendance_factor, 4)

        radius = max(settings.EVENT_DEFAULT_RADIUS_KM, 0.1)
        dist = max(record.distance_km, 0.05)
        proximity_factor = max(0.2, 1.0 - (dist / radius) ** 0.8)
        factors["proximity_factor"] = round(proximity_factor, 4)

        hours_until = self._hours_until(record.start_at, now)
        urgency_factor = self._urgency_factor(hours_until)
        factors["urgency_factor"] = round(urgency_factor, 4)

        trend_boost = 1.0 + (record.trend_interest / 100.0) * 0.25
        factors["trend_boost"] = round(trend_boost, 4)

        sentiment_mod = {"positive": 1.1, "negative": 0.85, "neutral": 1.0}.get(
            record.news_sentiment, 1.0
        )
        factors["sentiment_modifier"] = sentiment_mod

        raw = (
            cat_weight
            * attendance_factor
            * proximity_factor
            * urgency_factor
            * trend_boost
            * sentiment_mod
        )
        impact_score = round(min(100.0, raw * 100.0), 2)
        return impact_score, factors, hours_until

    def build_classified(
        self,
        record: RawEventRecord,
        now: Optional[datetime] = None,
    ) -> ClassifiedEvent:
        now = now or datetime.now(timezone.utc)
        category, confidence = self.classifier.classify(record)
        impact_score, factors, hours_until = self.score_raw(record, category, now)

        is_active = False
        if record.start_at and record.end_at:
            is_active = record.start_at <= now <= record.end_at
        elif record.start_at:
            is_active = record.start_at <= now <= record.start_at.replace(
                hour=23, minute=59
            )

        return ClassifiedEvent(
            external_id=record.external_id,
            name=record.name,
            category=category,
            category_label=self.classifier.label_for(category),
            start_at=record.start_at,
            end_at=record.end_at,
            attendance_est=record.attendance_est,
            distance_km=record.distance_km,
            venue_name=record.venue_name,
            source=record.source,
            impact_score=impact_score,
            impact_factors=factors,
            classification_confidence=confidence,
            trend_interest=record.trend_interest,
            news_sentiment=record.news_sentiment,
            hours_until_start=hours_until,
            is_active=is_active,
        )

    def aggregate_impact(self, events: list[ClassifiedEvent]) -> float:
        """Composite score: weighted max + count boost, capped at 100."""
        if not events:
            return 0.0
        scores = sorted((e.impact_score for e in events), reverse=True)
        top = scores[0]
        secondary = sum(s * 0.15 for s in scores[1:4])
        composite = min(100.0, top + secondary)
        return round(composite, 2)

    def _hours_until(
        self, start_at: Optional[datetime], now: datetime
    ) -> Optional[float]:
        if not start_at:
            return None
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=timezone.utc)
        delta = (start_at - now).total_seconds() / 3600.0
        return round(delta, 2)

    def _urgency_factor(self, hours_until: Optional[float]) -> float:
        if hours_until is None:
            return 0.75
        if hours_until < 0:
            return 1.0  # in progress
        if hours_until <= 6:
            return 1.0
        if hours_until <= 24:
            return 0.92
        if hours_until <= 72:
            return 0.80
        if hours_until <= 168:
            return 0.65
        return 0.50
