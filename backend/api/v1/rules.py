from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from uuid import UUID
from backend.api.deps import get_db, get_current_tenant_id
from backend.models.rule import PricingRule

router = APIRouter()

# --- Request / Response Schemas ---
class PricingRuleCreate(BaseModel):
    name: str
    rule_type: str = Field(description="weather, event, inventory, time_of_day")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Rule specific parameters")
    adjustment_type: str = Field(description="percentage, fixed")
    adjustment_value: float = Field(description="Positive values for markups, negative for markdowns")
    is_active: bool = True

class PricingRuleUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    adjustment_type: Optional[str] = None
    adjustment_value: Optional[float] = None
    is_active: Optional[bool] = None

class PricingRuleResponse(BaseModel):
    id: str
    name: str
    rule_type: str
    conditions: Dict[str, Any]
    adjustment_type: str
    adjustment_value: float
    is_active: bool
    created_at: datetime

# --- Endpoints ---

@router.get("", response_model=List[PricingRuleResponse])
def list_rules(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    rules = db.exec(
        select(PricingRule).where(PricingRule.tenant_id == tenant_id)
    ).all()
    return rules

@router.post("", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: PricingRuleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    if payload.rule_type not in ["weather", "event", "inventory", "time_of_day"]:
        raise HTTPException(
            status_code=400,
            detail="Rule type must be weather, event, inventory, or time_of_day."
        )
        
    if payload.adjustment_type not in ["percentage", "fixed"]:
        raise HTTPException(
            status_code=400,
            detail="Adjustment type must be percentage or fixed."
        )

    rule = PricingRule(
        tenant_id=tenant_id,
        name=payload.name,
        rule_type=payload.rule_type,
        conditions=payload.conditions,
        adjustment_type=payload.adjustment_type,
        adjustment_value=payload.adjustment_value,
        is_active=payload.is_active
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.patch("/{id}", response_model=PricingRuleResponse)
def update_rule(
    id: UUID,
    payload: PricingRuleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    rule = db.exec(
        select(PricingRule).where(PricingRule.tenant_id == tenant_id, PricingRule.id == id)
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    
    if "rule_type" in update_data and update_data["rule_type"] not in ["weather", "event", "inventory", "time_of_day"]:
         raise HTTPException(status_code=400, detail="Invalid rule type.")
         
    if "adjustment_type" in update_data and update_data["adjustment_type"] not in ["percentage", "fixed"]:
         raise HTTPException(status_code=400, detail="Invalid adjustment type.")

    for key, value in update_data.items():
        setattr(rule, key, value)
        
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    rule = db.exec(
        select(PricingRule).where(PricingRule.tenant_id == tenant_id, PricingRule.id == id)
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
        
    db.delete(rule)
    db.commit()
    return
