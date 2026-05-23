from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

class PricingRule(SQLModel, table=True):
    __tablename__ = "pricing_rules"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    name: str = Field(max_length=255)
    rule_type: str = Field(max_length=50) # 'weather', 'event', 'inventory', 'time_of_day'
    
    # Conditions stored as JSON (e.g., {"weather": "Rainy", "temp_below": 15})
    conditions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    
    adjustment_type: str = Field(max_length=20) # 'percentage', 'fixed'
    adjustment_value: float # e.g. 10.0 representing 10% or 10.0 for $10
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="rules")
    recommendations: list["Recommendation"] = Relationship(back_populates="rule")
from backend.models.recommendation import Recommendation
