"""Data source clients — NewsAPI, Google Trends, PredictHQ / event APIs."""

from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.core.config import settings
from backend.services.event_intelligence.schemas import EventSource, RawEventRecord

logger = logging.getLogger(__name__)

MONITORED_TREND_KEYWORDS = [
    "IPL",
    "cricket match",
    "football match",
    "Durga Puja",
    "college fest",
    "public holiday",
    "local festival",
]


class NewsAPIEventSource:
    """Extracts event signals from NewsAPI headlines."""

    EVENT_QUERIES = [
        "IPL OR cricket match",
        "football match OR soccer",
        "Durga Puja OR festival",
        "college fest OR university festival",
        "public holiday",
        "local event OR concert",
    ]

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        city: str = "local",
    ) -> list[RawEventRecord]:
        if not settings.NEWS_API_KEY:
            return self._mock_records(latitude, longitude)

        records: list[RawEventRecord] = []
        async with httpx.AsyncClient() as client:
            for query in self.EVENT_QUERIES[:3]:
                params = {
                    "apiKey": settings.NEWS_API_KEY,
                    "q": query,
                    "pageSize": 3,
                    "sortBy": "publishedAt",
                    "language": "en",
                }
                try:
                    response = await client.get(
                        "https://newsapi.org/v2/everything",
                        params=params,
                        timeout=12.0,
                    )
                    if response.status_code != 200:
                        continue
                    for article in response.json().get("articles", []):
                        title = article.get("title") or "News Event"
                        records.append(
                            RawEventRecord(
                                external_id=self._id("news", title),
                                name=title,
                                description=article.get("description") or "",
                                raw_category=query.split(" OR ")[0],
                                start_at=self._parse_date(article.get("publishedAt")),
                                attendance_est=1500,
                                distance_km=2.0,
                                source=EventSource.NEWSAPI,
                                news_sentiment=self._sentiment(title),
                                raw_payload={"url": article.get("url")},
                            )
                        )
                except Exception as exc:
                    logger.warning("NewsAPI event fetch failed: %s", exc)
        return records[: settings.EVENT_MAX_PER_SOURCE]

    def _mock_records(self, lat: float, lon: float) -> list[RawEventRecord]:
        random.seed(int(lat * 40 + lon * 40))
        templates = [
            ("IPL Playoffs Watch Party Surge in City", "IPL", 8000, "positive"),
            ("Major Football Derby This Weekend", "football", 15000, "positive"),
            ("Durga Puja Pandals Draw Record Crowds", "Durga Puja", 25000, "positive"),
            ("University Tech Fest Opens Downtown", "college fest", 4000, "positive"),
            ("National Public Holiday — Stores See Footfall Shift", "holiday", 0, "neutral"),
        ]
        now = datetime.now(timezone.utc)
        out = []
        for i, (title, cat, att, sent) in enumerate(random.sample(templates, k=3)):
            start = now + timedelta(days=i, hours=random.randint(4, 20))
            out.append(
                RawEventRecord(
                    external_id=self._id("mock-news", title),
                    name=title,
                    description=f"Mock headline for {cat}",
                    raw_category=cat,
                    start_at=start,
                    end_at=start + timedelta(hours=5),
                    attendance_est=att,
                    distance_km=round(random.uniform(0.3, 2.5), 2),
                    source=EventSource.MOCK,
                    news_sentiment=sent,
                )
            )
        random.seed(None)
        return out

    @staticmethod
    def _id(prefix: str, text: str) -> str:
        return f"{prefix}-{hashlib.md5(text.encode()).hexdigest()[:12]}"

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _sentiment(title: str) -> str:
        lower = title.lower()
        if any(w in lower for w in ("flood", "strike", "cancel", "closure")):
            return "negative"
        if any(w in lower for w in ("fest", "record", "surge", "opening", "celebration")):
            return "positive"
        return "neutral"


class GoogleTrendsEventSource:
    """
    Surfaces trending interest for monitored keywords.
    Uses mock deterministic data when no SerpAPI key; optional SerpAPI for live trends.
    """

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        geo: str | None = None,
    ) -> list[RawEventRecord]:
        if settings.SERPAPI_KEY:
            return await self._fetch_serpapi(latitude, longitude, geo)
        return self._mock_trends(latitude, longitude)

    async def _fetch_serpapi(
        self,
        latitude: float,
        longitude: float,
        geo: str | None,
    ) -> list[RawEventRecord]:
        records: list[RawEventRecord] = []
        region = geo or settings.EVENT_TRENDS_GEO or "US"
        async with httpx.AsyncClient() as client:
            for keyword in MONITORED_TREND_KEYWORDS[:4]:
                params = {
                    "engine": "google_trends",
                    "q": keyword,
                    "geo": region,
                    "api_key": settings.SERPAPI_KEY,
                }
                try:
                    response = await client.get(
                        "https://serpapi.com/search.json",
                        params=params,
                        timeout=15.0,
                    )
                    if response.status_code != 200:
                        continue
                    data = response.json()
                    interest = self._extract_interest(data)
                    if interest < 20:
                        continue
                    now = datetime.now(timezone.utc)
                    records.append(
                        RawEventRecord(
                            external_id=f"trend-{hashlib.md5(keyword.encode()).hexdigest()[:10]}",
                            name=f"Trending: {keyword}",
                            description="Google Trends interest spike",
                            raw_category="trends",
                            start_at=now,
                            end_at=now + timedelta(days=2),
                            attendance_est=int(interest * 100),
                            distance_km=0.0,
                            source=EventSource.GOOGLE_TRENDS,
                            trend_interest=float(interest),
                        )
                    )
                except Exception as exc:
                    logger.warning("SerpAPI trends failed for %s: %s", keyword, exc)
        return records

    def _mock_trends(self, lat: float, lon: float) -> list[RawEventRecord]:
        random.seed(int(lat * 30 + lon * 30) + datetime.now(timezone.utc).day)
        now = datetime.now(timezone.utc)
        picks = random.sample(MONITORED_TREND_KEYWORDS, k=3)
        records = []
        for kw in picks:
            interest = random.randint(45, 98)
            records.append(
                RawEventRecord(
                    external_id=f"mock-trend-{hashlib.md5(kw.encode()).hexdigest()[:8]}",
                    name=f"Trending: {kw}",
                    description="Mock Google Trends signal",
                    raw_category="trends",
                    start_at=now,
                    end_at=now + timedelta(days=1),
                    attendance_est=interest * 80,
                    distance_km=0.0,
                    source=EventSource.MOCK,
                    trend_interest=float(interest),
                )
            )
        random.seed(None)
        return records

    @staticmethod
    def _extract_interest(data: dict[str, Any]) -> float:
        timeline = (
            data.get("interest_over_time", {}).get("timeline_data")
            or data.get("timeline_data")
            or []
        )
        if not timeline:
            return 50.0
        last = timeline[-1]
        values = last.get("values") or []
        if values:
            return float(values[0].get("extracted_value") or values[0].get("value") or 50)
        return 50.0


class PredictHQEventSource:
    """Event API client — PredictHQ with mock fallback."""

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        radius_km: float | None = None,
    ) -> list[RawEventRecord]:
        radius = radius_km or settings.EVENT_DEFAULT_RADIUS_KM
        if not settings.PREDICTHQ_API_KEY:
            return self._mock_events(latitude, longitude)

        url = "https://api.predicthq.com/v1/events/"
        headers = {
            "Authorization": f"Bearer {settings.PREDICTHQ_API_KEY}",
            "Accept": "application/json",
        }
        params = {
            "within": f"{radius}km@{latitude},{longitude}",
            "active.gte": datetime.now(timezone.utc).isoformat(),
            "limit": settings.EVENT_MAX_PER_SOURCE,
        }
        records: list[RawEventRecord] = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=12.0)
                if response.status_code != 200:
                    logger.error("PredictHQ failed: %s", response.text)
                    return self._mock_events(latitude, longitude)
                for ev in response.json().get("results", []):
                    records.append(self._parse_predicthq(ev))
            except Exception as exc:
                logger.error("PredictHQ error: %s", exc)
                return self._mock_events(latitude, longitude)
        return records

    def _parse_predicthq(self, ev: dict[str, Any]) -> RawEventRecord:
        start = ev.get("start")
        end = ev.get("end")
        return RawEventRecord(
            external_id=str(ev.get("id") or ev.get("phq_id") or "phq-unknown"),
            name=ev.get("title") or "Event",
            description=ev.get("description") or "",
            raw_category=str(ev.get("category") or ""),
            start_at=self._iso(start),
            end_at=self._iso(end),
            attendance_est=int(ev.get("phq_attendance") or 500),
            distance_km=1.0,
            venue_name=(ev.get("entities") or [{}])[0].get("name", "")
            if ev.get("entities")
            else "",
            source=EventSource.PREDICTHQ,
            raw_payload=ev,
        )

    def _mock_events(self, lat: float, lon: float) -> list[RawEventRecord]:
        random.seed(int(lat * 50 + lon * 50))
        templates = [
            ("IPL Final Watch Zone", "sports", 18000, 0.6),
            ("Champions League Screening", "sports", 9000, 1.1),
            ("Durga Puja Cultural Fair", "festivals", 22000, 0.4),
            ("State University Annual Fest", "conferences", 3500, 0.9),
            ("Independence Day Parade", "community", 12000, 1.3),
            ("Neighborhood Street Fair", "festivals", 1200, 0.3),
        ]
        num = random.randint(2, 4)
        selected = random.sample(templates, k=min(num, len(templates)))
        now = datetime.now(timezone.utc)
        events = []
        for name, cat, att, dist in selected:
            offset = random.randint(0, 2)
            start = now + timedelta(days=offset, hours=random.randint(2, 10))
            events.append(
                RawEventRecord(
                    external_id=f"mock-phq-{hashlib.md5(name.encode()).hexdigest()[:10]}",
                    name=name,
                    raw_category=cat,
                    start_at=start,
                    end_at=start + timedelta(hours=random.randint(3, 6)),
                    attendance_est=att,
                    distance_km=dist,
                    source=EventSource.MOCK,
                )
            )
        random.seed(None)
        return events

    @staticmethod
    def _iso(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
