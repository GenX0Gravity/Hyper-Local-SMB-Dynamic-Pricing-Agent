from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from uuid import UUID
from backend.api.deps import get_db, get_current_tenant_id
from backend.models.tenant import Tenant

router = APIRouter()

# --- Request / Response Schemas ---
class TenantUpdate(BaseModel):
    name: Optional[str] = None
    business_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_auto_approve: Optional[bool] = None
    currency: Optional[str] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    business_type: str
    latitude: float
    longitude: float
    timezone: str
    whatsapp_phone: Optional[str]
    whatsapp_enabled: bool
    whatsapp_auto_approve: bool = False
    currency: str

# --- Endpoints ---

@router.get("", response_model=TenantResponse)
def get_store_settings(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Store configurations not found")
    return tenant

@router.patch("", response_model=TenantResponse)
def update_store_settings(
    payload: TenantUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Store configurations not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)
        
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant
