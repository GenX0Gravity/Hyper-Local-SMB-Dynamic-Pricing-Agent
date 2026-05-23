"""Event classification logic — maps raw records to monitored categories."""

from __future__ import annotations

import re
from typing import Pattern

from backend.services.event_intelligence.schemas import EventCategory, RawEventRecord

# Keyword patterns per monitored event type (case-insensitive)
_CATEGORY_PATTERNS: list[tuple[EventCategory, list[Pattern[str]]]] = [
    (
        EventCategory.IPL_MATCH,
        [
            re.compile(p, re.I)
            for p in (
                r"\bipl\b",
                r"indian premier league",
                r"\bt20\b.*\bindia\b",
                r"cricket match",
                r"\bmi\b vs|\brcb\b vs|\bcsk\b vs",
            )
        ],
    ),
    (
        EventCategory.FOOTBALL_MATCH,
        [
            re.compile(p, re.I)
            for p in (
                r"football match",
                r"soccer match",
                r"\bpremier league\b",
                r"\blaliga\b",
                r"\buefa\b",
                r"\bfifa\b",
                r"world cup.*football",
                r"\bisl\b.*match",
                r"derby",
            )
        ],
    ),
    (
        EventCategory.DURGA_PUJA,
        [
            re.compile(p, re.I)
            for p in (
                r"durga puja",
                r"durgotsav",
                r"pandal",
                r"puja pandals",
                r"mahalaya",
                r"vijaya dashami",
            )
        ],
    ),
    (
        EventCategory.COLLEGE_FESTIVAL,
        [
            re.compile(p, re.I)
            for p in (
                r"college fest",
                r"university fest",
                r"cultural fest",
                r"tech fest",
                r"college festival",
                r"campus fest",
                r"\bfest\b.*\b(college|university|campus)\b",
            )
        ],
    ),
    (
        EventCategory.PUBLIC_HOLIDAY,
        [
            re.compile(p, re.I)
            for p in (
                r"public holiday",
                r"national holiday",
                r"bank holiday",
                r"independence day",
                r"republic day",
                r"diwali holiday",
                r"christmas day",
                r"new year.*holiday",
                r"holiday closure",
            )
        ],
    ),
]

# PredictHQ / generic API category hints
_API_CATEGORY_MAP: dict[str, EventCategory] = {
    "sports": EventCategory.FOOTBALL_MATCH,
    "sport": EventCategory.FOOTBALL_MATCH,
    "concerts": EventCategory.LOCAL_EVENT,
    "festivals": EventCategory.LOCAL_EVENT,
    "community": EventCategory.LOCAL_EVENT,
    "conferences": EventCategory.COLLEGE_FESTIVAL,
    "public-holidays": EventCategory.PUBLIC_HOLIDAY,
    "holidays": EventCategory.PUBLIC_HOLIDAY,
    "school-holidays": EventCategory.PUBLIC_HOLIDAY,
}


class EventClassifier:
    """Classifies raw events into IPL, football, Durga Puja, college fest, holiday, or local."""

    CATEGORY_LABELS: dict[EventCategory, str] = {
        EventCategory.IPL_MATCH: "IPL Match",
        EventCategory.FOOTBALL_MATCH: "Football Match",
        EventCategory.DURGA_PUJA: "Durga Puja",
        EventCategory.COLLEGE_FESTIVAL: "College Festival",
        EventCategory.PUBLIC_HOLIDAY: "Public Holiday",
        EventCategory.LOCAL_EVENT: "Local Event",
        EventCategory.UNKNOWN: "Unknown",
    }

    def classify(self, record: RawEventRecord) -> tuple[EventCategory, float]:
        """
        Returns (category, confidence 0–1).
        Priority: explicit keywords → API category hint → local default.
        """
        text = " ".join(
            filter(
                None,
                [
                    record.name,
                    record.description,
                    record.raw_category,
                    record.venue_name,
                ],
            )
        )

        for category, patterns in _CATEGORY_PATTERNS:
            for pattern in patterns:
                if pattern.search(text):
                    return category, 0.92

        api_hint = (record.raw_category or "").lower().replace(" ", "-")
        if api_hint in _API_CATEGORY_MAP:
            return _API_CATEGORY_MAP[api_hint], 0.75

        if record.source.value == "google_trends" and record.trend_interest >= 60:
            return self._classify_from_trend_keyword(record.name), 0.70

        if record.attendance_est >= 5000:
            return EventCategory.LOCAL_EVENT, 0.55

        return EventCategory.LOCAL_EVENT, 0.50

    def _classify_from_trend_keyword(self, name: str) -> EventCategory:
        lower = name.lower()
        if "ipl" in lower or "cricket" in lower:
            return EventCategory.IPL_MATCH
        if any(w in lower for w in ("football", "soccer", "premier league")):
            return EventCategory.FOOTBALL_MATCH
        if "durga" in lower or "puja" in lower:
            return EventCategory.DURGA_PUJA
        if "fest" in lower or "college" in lower:
            return EventCategory.COLLEGE_FESTIVAL
        if "holiday" in lower:
            return EventCategory.PUBLIC_HOLIDAY
        return EventCategory.LOCAL_EVENT

    def label_for(self, category: EventCategory) -> str:
        return self.CATEGORY_LABELS.get(category, "Event")
