from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from uuid import UUID
from backend.api.deps import get_db, get_current_tenant_id
from backend.models.signal import DemandSignal

router = APIRouter()

# --- Response Schemas ---
class SignalResponse(BaseModel):
    id: str
    signal_type: str
    value: Dict[str, Any]
    recorded_at: str

@router.get("/weather", response_model=Optional[SignalResponse])
def get_latest_weather_signal(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    signal = db.exec(
        select(DemandSignal)
        .where(DemandSignal.tenant_id == tenant_id, DemandSignal.signal_type == "weather")
        .order_by(DemandSignal.recorded_at.desc())
    ).first()
    
    if not signal:
        return None
        
    return SignalResponse(
        id=str(signal.id),
        signal_type=signal.signal_type,
        value=signal.value,
        recorded_at=signal.recorded_at.isoformat()
    )

@router.get("/events", response_model=List[SignalResponse])
def get_recent_event_signals(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    # Fetch events logged in the last 24 hours
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    
    signals = db.exec(
        select(DemandSignal)
        .where(
            DemandSignal.tenant_id == tenant_id,
            DemandSignal.signal_type == "event",
            DemandSignal.recorded_at >= cutoff
        )
        .order_by(DemandSignal.recorded_at.desc())
    ).all()
    
    return [
        SignalResponse(
            id=str(s.id),
            signal_type=s.signal_type,
            value=s.value,
            recorded_at=s.recorded_at.isoformat()
        ) for s in signals
    ]
