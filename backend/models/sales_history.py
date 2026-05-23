from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class SalesHistory(SQLModel, table=True):
    __tablename__ = "sales_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    product_id: UUID = Field(foreign_key="products.id")
    quantity: int
    price_sold: float
    sold_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="sales")
    product: Optional["Product"] = Relationship(back_populates="sales")
