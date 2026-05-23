from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import httpx

app = FastAPI(title="PricePulse LangGraph Agent")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    text: str

@app.post("/agent/query", response_model=QueryResponse)
async def query_agent(req: QueryRequest):
    """Simple agent endpoint that proxies to OpenAI if available, else returns a heuristic reply."""
    if OPENAI_API_KEY:
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            body = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": req.prompt}],
                "max_tokens": 500,
            }
            try:
                r = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return {"text": text}
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}")
    # Fallback heuristic reply
    reply = f"[simulated agent reply] Received: {req.prompt[:200]}"
    return {"text": reply}
