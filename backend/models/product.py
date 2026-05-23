from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    sku: Optional[str] = Field(default=None, max_length=100)
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, max_length=100)
    cost_price: float
    base_price: float
    current_price: float
    max_price: Optional[float] = Field(default=None)
    min_price: Optional[float] = Field(default=None)
    stock_qty: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="products")
    recommendations: List["Recommendation"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    sales: List["SalesHistory"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
