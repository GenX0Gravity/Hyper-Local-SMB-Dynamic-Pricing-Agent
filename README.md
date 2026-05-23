# PricePulse AI — MVP

This workspace contains an MVP for PricePulse AI: an end-to-end dynamic pricing pipeline.

Services:
- PostgreSQL
- Redis
- FastAPI backend (pricepulse_api)
- Celery worker and beat for scheduled tasks
- LangGraph-compatible agent (pricepulse_langgraph)
- Next.js frontend (pricepulse_frontend)

Quick start (Docker):

1. Copy `.env.example` to `.env` and fill any provider keys (OpenAI, Twilio, OpenWeatherMap).

2. Build and start services:

```bash
docker compose up --build
```

3. Open the API docs:

- FastAPI docs: http://localhost:8000/docs
- Next.js frontend: http://localhost:3000
- LangGraph agent (simple proxy): http://localhost:8100/docs

Notes:
- The orchestrator endpoint is at `/api/v1/orchestrator/trigger` and runs Weather → Events → Forecast → Pricing → WhatsApp (best-effort).
- Configure Twilio and OpenAI keys in `.env` to enable notifications and agent features.

If you want me to run the app locally or add CI, tell me which step to do next.
