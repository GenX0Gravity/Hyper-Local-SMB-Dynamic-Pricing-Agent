from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    product_id: UUID = Field(foreign_key="products.id")
    rule_id: Optional[UUID] = Field(default=None, foreign_key="pricing_rules.id")
    
    recommended_price: float
    previous_price: float
    reason: str
    status: str = Field(default="pending", max_length=50) # 'pending', 'approved', 'rejected', 'auto_applied'
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="recommendations")
    product: Optional["Product"] = Relationship(back_populates="recommendations")
    rule: Optional["PricingRule"] = Relationship(back_populates="recommendations")
    audits: List["RecommendationAudit"] = Relationship(back_populates="recommendation", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class RecommendationAudit(SQLModel, table=True):
    __tablename__ = "recommendation_audits"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    recommendation_id: UUID = Field(foreign_key="recommendations.id")
    action: str = Field(max_length=50) # 'approved', 'rejected', 'auto_applied'
    changed_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    recommendation: Optional[Recommendation] = Relationship(back_populates="audits")
