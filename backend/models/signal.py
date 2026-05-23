from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

class DemandSignal(SQLModel, table=True):
    __tablename__ = "demand_signals"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    signal_type: str = Field(max_length=50) # 'weather', 'event', 'foot_traffic'
    
    # Store signal payload (e.g. {"temp": 12.5, "condition": "Rainy"})
    value: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="signals")
