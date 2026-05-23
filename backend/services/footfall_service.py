"""Google Maps Popular Times / footfall proxy."""

import logging
import random
from datetime import datetime, timezone
from typing import Any

from backend.core.config import settings

logger = logging.getLogger(__name__)


class FootfallService:
    @staticmethod
    async def get_popular_times(
        latitude: float, longitude: float, place_name: str = "store"
    ) -> dict[str, Any]:
        """
        Returns foot-traffic intensity for the current hour.
        Uses Google Places Popular Times when GOOGLE_MAPS_API_KEY is set;
        otherwise returns a deterministic mock keyed on coordinates.
        """
        if not settings.GOOGLE_MAPS_API_KEY:
            return FootfallService._mock_popular_times(latitude, longitude)

        # Production: call Places API (New) or legacy popular_times field when available
        logger.info("Google Maps API key present; using mock until Places integration is wired.")
        return FootfallService._mock_popular_times(latitude, longitude)

    @staticmethod
    def _mock_popular_times(latitude: float, longitude: float) -> dict[str, Any]:
        hour = datetime.now(timezone.utc).hour
        seed = int(latitude * 1000 + longitude * 1000)
        random.seed(seed + hour)
        busy_pct = random.randint(20, 95)
        random.seed(None)
        return {
            "busy_percent": busy_pct,
            "current_hour": hour,
            "peak_expected": busy_pct >= 70,
            "visitor_index": round(busy_pct / 50.0, 2),
            "source": "MockPopularTimes",
        }


footfall_service = FootfallService()
