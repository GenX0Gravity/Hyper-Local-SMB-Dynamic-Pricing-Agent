"""NewsAPI local sentiment / demand shock signals."""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class NewsService:
    @staticmethod
    async def get_local_headlines(
        city: str = "local", country: str = "us", page_size: int = 5
    ) -> list[dict[str, Any]]:
        if not settings.NEWS_API_KEY:
            return NewsService._mock_headlines(city)

        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "apiKey": settings.NEWS_API_KEY,
            "country": country,
            "pageSize": page_size,
            "q": city if city != "local" else None,
        }
        params = {k: v for k, v in params.items() if v is not None}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    articles = response.json().get("articles", [])
                    return [
                        {
                            "title": a.get("title"),
                            "description": a.get("description"),
                            "published_at": a.get("publishedAt"),
                            "sentiment_hint": NewsService._headline_sentiment(
                                a.get("title", "")
                            ),
                            "source": "NewsAPI",
                        }
                        for a in articles[:page_size]
                    ]
                logger.error("NewsAPI error: %s", response.text)
            except Exception as exc:
                logger.error("NewsAPI request failed: %s", exc)

        return NewsService._mock_headlines(city)

    @staticmethod
    def _headline_sentiment(title: str) -> str:
        negative = ("strike", "closure", "flood", "crime", "outbreak")
        positive = ("festival", "opening", "boom", "record", "celebration")
        lower = title.lower()
        if any(w in lower for w in negative):
            return "negative"
        if any(w in lower for w in positive):
            return "positive"
        return "neutral"

    @staticmethod
    def _mock_headlines(city: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "title": f"Downtown {city} foot traffic surges ahead of weekend",
                "description": "Retailers report higher walk-in volume.",
                "published_at": now,
                "sentiment_hint": "positive",
                "source": "MockNews",
            },
            {
                "title": "Roadworks may reduce access to main shopping strip",
                "description": "Temporary lane closures this week.",
                "published_at": now,
                "sentiment_hint": "negative",
                "source": "MockNews",
            },
        ]


news_service = NewsService()
