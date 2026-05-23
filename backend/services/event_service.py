import httpx
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from backend.core.config import settings

logger = logging.getLogger(__name__)

class EventService:
    @staticmethod
    async def get_upcoming_events(latitude: float, longitude: float, radius_km: float = 2.0) -> List[Dict[str, Any]]:
        """
        Fetches local events near a coordinate.
        Falls back to a mock local event generator if no PredictHQ key is configured.
        """
        if not settings.PREDICTHQ_API_KEY:
            logger.info("No PREDICTHQ_API_KEY set. Generating mock events telemetry.")
            
            # Deterministic generation based on store location
            random.seed(int(latitude * 50 + longitude * 50))
            
            event_templates = [
                {"name": "Local Music Festival", "category": "concerts", "attendance": 5000, "dist": 0.5},
                {"name": "Football Match", "category": "sports", "attendance": 12000, "dist": 1.2},
                {"name": "Farmers Market", "category": "community", "attendance": 800, "dist": 0.2},
                {"name": "Boutique Fashion Show", "category": "conferences", "attendance": 300, "dist": 0.8},
                {"name": "Street Parade", "category": "festivals", "attendance": 3500, "dist": 0.4},
                {"name": "Tech Conference", "category": "conferences", "attendance": 1500, "dist": 1.5}
            ]
            
            # Pick a subset of 1 to 3 events
            num_events = random.randint(1, 3)
            selected = random.sample(event_templates, k=num_events)
            
            events = []
            for item in selected:
                # Set times: some today, some tomorrow
                offset_days = random.randint(0, 1)
                start = datetime.now(timezone.utc) + timedelta(days=offset_days, hours=random.randint(2, 8))
                
                events.append({
                    "name": item["name"],
                    "category": item["category"],
                    "attendance": item["attendance"],
                    "distance_km": item["dist"],
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=4)).isoformat(),
                    "source": "MockTelemetry"
                })
                
            random.seed(None)
            return events

        # Real PredictHQ client would run HTTP requests
        url = "https://api.predicthq.com/v1/events/"
        headers = {"Authorization": f"Bearer {settings.PREDICTHQ_API_KEY}", "Accept": "application/json"}
        params = {
            "within": f"{radius_km}km@{latitude},{longitude}",
            "active.gte": datetime.now(timezone.utc).isoformat(),
            "limit": 10
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for ev in data.get("results", []):
                        # Extract distance if available, otherwise estimate
                        results.append({
                            "name": ev.get("title"),
                            "category": ev.get("category"),
                            "attendance": ev.get("phq_attendance", 500),
                            "distance_km": 1.0, # PredictHQ returns coordinates, calculation omitted for brevity
                            "start_time": ev.get("start"),
                            "end_time": ev.get("end"),
                            "source": "PredictHQ"
                        })
                    return results
                else:
                    logger.error(f"PredictHQ API failed: {response.text}")
            except Exception as e:
                logger.error(f"Error connecting to PredictHQ API: {str(e)}")

        return []

event_service = EventService()
