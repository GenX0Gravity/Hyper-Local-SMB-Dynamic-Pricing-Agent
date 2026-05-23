from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from uuid import UUID
from backend.api.deps import get_db, get_current_tenant_id, get_current_user
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.product import Product
from backend.models.signal import DemandSignal
from backend.models.recommendation import Recommendation, RecommendationAudit
from backend.services.pricing_engine import PricingEngine
from backend.services.weather_service import weather_service
from backend.services.event_service import event_service
from backend.services.whatsapp_service import whatsapp_service

router = APIRouter()

# --- Request / Response Schemas ---
class ProductSnippet(BaseModel):
    id: str
    name: str
    category: Optional[str]
    sku: Optional[str]
    base_price: float
    current_price: float

class RecommendationResponse(BaseModel):
    id: str
    tenant_id: str
    product_id: str
    product: ProductSnippet
    rule_id: Optional[str]
    rule_name: Optional[str]
    recommended_price: float
    previous_price: float
    reason: str
    status: str
    created_at: datetime
    expires_at: datetime

# --- Endpoints ---

@router.get("", response_model=List[RecommendationResponse])
def list_recommendations(
    status_filter: Optional[str] = "pending",
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    query = select(Recommendation).where(Recommendation.tenant_id == tenant_id)
    if status_filter:
        query = query.where(Recommendation.status == status_filter)
        
    query = query.order_by(Recommendation.created_at.desc())
    recommendations = db.exec(query).all()
    
    results = []
    for rec in recommendations:
        product = db.exec(select(Product).where(Product.id == rec.product_id)).first()
        if not product:
            continue
            
        rule_name = None
        if rec.rule_id:
            from backend.models.rule import PricingRule
            rule = db.exec(select(PricingRule).where(PricingRule.id == rec.rule_id)).first()
            rule_name = rule.name if rule else None

        results.append(
            RecommendationResponse(
                id=str(rec.id),
                tenant_id=str(rec.tenant_id),
                product_id=str(rec.product_id),
                product=ProductSnippet(
                    id=str(product.id),
                    name=product.name,
                    category=product.category,
                    sku=product.sku,
                    base_price=product.base_price,
                    current_price=product.current_price
                ),
                rule_id=str(rec.rule_id) if rec.rule_id else None,
                rule_name=rule_name,
                recommended_price=rec.recommended_price,
                previous_price=rec.previous_price,
                reason=rec.reason,
                status=rec.status,
                created_at=rec.created_at,
                expires_at=rec.expires_at
            )
        )
    return results

@router.post("/evaluate", response_model=List[RecommendationResponse])
async def evaluate_prices(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Manually triggers the evaluation engine for a tenant.
    Fetches latest weather and event signals and feeds them into the PricingEngine.
    """
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant store details not found")
        
    # 1. Fetch current weather and events
    weather_info = await weather_service.get_current_weather(tenant.latitude, tenant.longitude)
    events_info = await event_service.get_upcoming_events(tenant.latitude, tenant.longitude)
    
    # 2. Save signals to database
    db_weather_signal = DemandSignal(
        tenant_id=tenant_id,
        signal_type="weather",
        value=weather_info
    )
    db.add(db_weather_signal)
    
    db_event_signals = []
    for ev in events_info:
        db_ev = DemandSignal(
            tenant_id=tenant_id,
            signal_type="event",
            value=ev
        )
        db.add(db_ev)
        db_event_signals.append(db_ev)
        
    db.commit()
    
    # Gather signals for engine check
    active_signals = [db_weather_signal] + db_event_signals
    
    # 3. Evaluate prices
    recs = PricingEngine.evaluate_rules(db, tenant_id, active_signals)
    
    # 4. Trigger WhatsApp alerts for any new pending recommendations
    if recs and tenant.whatsapp_enabled and tenant.whatsapp_phone:
        whatsapp_body = f"PricePulse AI: {len(recs)} new pricing recommendations generated for {tenant.name}. Review them on your dashboard."
        await whatsapp_service.send_whatsapp_message(tenant.whatsapp_phone, whatsapp_body)
        
    # Return evaluated recommendation objects with nested details
    # We trigger the list recommendation mapping
    return list_recommendations(status_filter="pending", tenant_id=tenant_id, db=db)

@router.post("/{id}/apply", response_model=RecommendationResponse)
def apply_recommendation(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id
    rec = db.exec(
        select(Recommendation).where(
            Recommendation.id == id,
            Recommendation.tenant_id == tenant_id
        )
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation suggestion not found")
        
    if rec.status != "pending":
        raise HTTPException(status_code=400, detail=f"Recommendation is already in status '{rec.status}'")

    product = db.exec(select(Product).where(Product.id == rec.product_id)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Associated product not found")

    # 1. Update product active price
    rec.previous_price = product.current_price
    product.current_price = rec.recommended_price
    product.updated_at = datetime.now(timezone.utc)
    db.add(product)

    # 2. Update recommendation status
    rec.status = "approved"
    db.add(rec)

    # 3. Log Audit trail
    audit = RecommendationAudit(
        recommendation_id=rec.id,
        action="approved",
        changed_by=current_user.id
    )
    db.add(audit)
    
    db.commit()
    db.refresh(rec)
    db.refresh(product)
    
    rule_name = None
    if rec.rule_id:
        from backend.models.rule import PricingRule
        rule = db.exec(select(PricingRule).where(PricingRule.id == rec.rule_id)).first()
        rule_name = rule.name if rule else None
        
    return RecommendationResponse(
        id=str(rec.id),
        tenant_id=str(rec.tenant_id),
        product_id=str(rec.product_id),
        product=ProductSnippet(
            id=str(product.id),
            name=product.name,
            category=product.category,
            sku=product.sku,
            base_price=product.base_price,
            current_price=product.current_price
        ),
        rule_id=str(rec.rule_id) if rec.rule_id else None,
        rule_name=rule_name,
        recommended_price=rec.recommended_price,
        previous_price=rec.previous_price,
        reason=rec.reason,
        status=rec.status,
        created_at=rec.created_at,
        expires_at=rec.expires_at
    )

@router.post("/{id}/reject", response_model=RecommendationResponse)
def reject_recommendation(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id
    rec = db.exec(
        select(Recommendation).where(
            Recommendation.id == id,
            Recommendation.tenant_id == tenant_id
        )
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation suggestion not found")
        
    if rec.status != "pending":
        raise HTTPException(status_code=400, detail=f"Recommendation is already in status '{rec.status}'")

    # 1. Update status
    rec.status = "rejected"
    db.add(rec)

    # 2. Log Audit trail
    audit = RecommendationAudit(
        recommendation_id=rec.id,
        action="rejected",
        changed_by=current_user.id
    )
    db.add(audit)
    
    db.commit()
    db.refresh(rec)
    
    product = db.exec(select(Product).where(Product.id == rec.product_id)).first()
    rule_name = None
    if rec.rule_id:
        from backend.models.rule import PricingRule
        rule = db.exec(select(PricingRule).where(PricingRule.id == rec.rule_id)).first()
        rule_name = rule.name if rule else None

    return RecommendationResponse(
        id=str(rec.id),
        tenant_id=str(rec.tenant_id),
        product_id=str(rec.product_id),
        product=ProductSnippet(
            id=str(product.id),
            name=product.name,
            category=product.category,
            sku=product.sku,
            base_price=product.base_price,
            current_price=product.current_price
        ),
        rule_id=str(rec.rule_id) if rec.rule_id else None,
        rule_name=rule_name,
        recommended_price=rec.recommended_price,
        previous_price=rec.previous_price,
        reason=rec.reason,
        status=rec.status,
        created_at=rec.created_at,
        expires_at=rec.expires_at
    )
