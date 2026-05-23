"""Event Intelligence data pipeline — ingest, classify, score, deduplicate."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.event_intelligence.scoring import EventImpactScorer
from backend.services.event_intelligence.schemas import (
    CategoryImpactSummary,
    ClassifiedEvent,
    EventCategory,
    RawEventRecord,
)
from backend.services.event_intelligence.sources import (
    GoogleTrendsEventSource,
    NewsAPIEventSource,
    PredictHQEventSource,
)

logger = logging.getLogger(__name__)


class EventDataPipeline:
    """
    Orchestrates multi-source ingestion:
      NewsAPI → Google Trends → Event APIs (PredictHQ)
    Then classification, impact scoring, and deduplication.
    """

    def __init__(
        self,
        news: NewsAPIEventSource | None = None,
        trends: GoogleTrendsEventSource | None = None,
        events_api: PredictHQEventSource | None = None,
        scorer: EventImpactScorer | None = None,
    ):
        self.news = news or NewsAPIEventSource()
        self.trends = trends or GoogleTrendsEventSource()
        self.events_api = events_api or PredictHQEventSource()
        self.scorer = scorer or EventImpactScorer()
        self.classifier = self.scorer.classifier

    async def run(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 2.0,
        city: str = "local",
        trends_geo: str | None = None,
    ) -> tuple[list[ClassifiedEvent], dict[str, Any]]:
        stats: dict[str, Any] = {
            "sources": [],
            "raw_count": 0,
            "deduped_count": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        news_task = self.news.fetch(latitude, longitude, city=city)
        trends_task = self.trends.fetch(latitude, longitude, geo=trends_geo)
        api_task = self.events_api.fetch(latitude, longitude, radius_km=radius_km)

        news_raw, trends_raw, api_raw = await asyncio.gather(
            news_task, trends_task, api_task, return_exceptions=True
        )

        raw_records: list[RawEventRecord] = []
        for label, result in (
            ("newsapi", news_raw),
            ("google_trends", trends_raw),
            ("predicthq", api_raw),
        ):
            if isinstance(result, Exception):
                logger.warning("Pipeline source %s failed: %s", label, result)
                stats.setdefault("errors", []).append({label: str(result)})
                continue
            stats["sources"].append(label)
            raw_records.extend(result)

        stats["raw_count"] = len(raw_records)
        deduped = self._deduplicate(raw_records)
        stats["deduped_count"] = len(deduped)

        now = datetime.now(timezone.utc)
        classified = [self.scorer.build_classified(r, now=now) for r in deduped]
        classified.sort(key=lambda e: e.impact_score, reverse=True)

        stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        return classified, stats

    def summarize_by_category(
        self, events: list[ClassifiedEvent]
    ) -> list[CategoryImpactSummary]:
        buckets: dict[EventCategory, list[ClassifiedEvent]] = {}
        for ev in events:
            buckets.setdefault(ev.category, []).append(ev)

        summaries = []
        for category, group in buckets.items():
            summaries.append(
                CategoryImpactSummary(
                    category=category,
                    event_count=len(group),
                    max_impact_score=max(e.impact_score for e in group),
                    total_attendance=sum(e.attendance_est for e in group),
                )
            )
        summaries.sort(key=lambda s: s.max_impact_score, reverse=True)
        return summaries

    def _deduplicate(self, records: list[RawEventRecord]) -> list[RawEventRecord]:
        seen: set[str] = set()
        unique: list[RawEventRecord] = []
        for record in records:
            key = self._fingerprint(record)
            if key in seen:
                continue
            seen.add(key)
            unique.append(record)
        return unique

    @staticmethod
    def _fingerprint(record: RawEventRecord) -> str:
        normalized = record.name.lower().strip()[:60]
        day = ""
        if record.start_at:
            day = record.start_at.date().isoformat()
        return f"{normalized}|{day}"
