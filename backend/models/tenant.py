from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(max_length=255, index=True)
    business_type: str = Field(max_length=50) # 'cafe', 'boutique', 'stationery', 'retail'
    latitude: float
    longitude: float
    timezone: str = Field(default="UTC", max_length=50)
    whatsapp_phone: Optional[str] = Field(default=None, max_length=20)
    whatsapp_enabled: bool = Field(default=False)
    currency: str = Field(default="USD", max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: List["User"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    products: List["Product"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    rules: List["PricingRule"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    recommendations: List["Recommendation"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    signals: List["DemandSignal"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    sales: List["SalesHistory"] = Relationship(back_populates="tenant", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
from backend.models.user import User
from backend.models.product import Product
from backend.models.rule import PricingRule
from backend.models.signal import DemandSignal
from backend.models.recommendation import Recommendation
from backend.models.sales_history import SalesHistory
