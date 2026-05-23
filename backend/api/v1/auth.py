from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from backend.api.deps import get_db, get_current_user
from backend.core.security import get_password_hash, verify_password, create_access_token
from backend.models.tenant import Tenant
from backend.models.user import User

router = APIRouter()

# --- Request / Response Schemas ---
class TenantRegistration(BaseModel):
    name: str
    business_type: str # 'cafe', 'boutique', 'stationery', 'retail'
    latitude: float
    longitude: float
    timezone: str = "UTC"
    whatsapp_phone: Optional[str] = None
    whatsapp_enabled: bool = False
    currency: str = "USD"

class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class RegisterRequest(BaseModel):
    tenant: TenantRegistration
    user: UserRegistration

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    full_name: str
    tenant_id: str

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_name: str

# --- Endpoints ---

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_tenant(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if user already exists
    existing_user = db.exec(select(User).where(User.email == data.user.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email address already exists."
        )
        
    try:
        # Create tenant
        db_tenant = Tenant(
            name=data.tenant.name,
            business_type=data.tenant.business_type,
            latitude=data.tenant.latitude,
            longitude=data.tenant.longitude,
            timezone=data.tenant.timezone,
            whatsapp_phone=data.tenant.whatsapp_phone,
            whatsapp_enabled=data.tenant.whatsapp_enabled,
            currency=data.tenant.currency
        )
        db.add(db_tenant)
        db.flush() # Populate db_tenant.id

        # Create user
        db_user = User(
            tenant_id=db_tenant.id,
            email=data.user.email,
            hashed_password=get_password_hash(data.user.password),
            full_name=data.user.full_name,
            role="owner",
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Issue token
        access_token = create_access_token(subject=db_user.id)
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=str(db_user.id),
            full_name=db_user.full_name,
            tenant_id=str(db_tenant.id)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database transaction failed during registration: {str(e)}"
        )

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User accounts is deactivated"
        )
        
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        full_name=user.full_name,
        tenant_id=str(user.tenant_id)
    )

@router.get("/me", response_model=UserProfile)
def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = db.exec(select(Tenant).where(Tenant.id == current_user.tenant_id)).first()
    tenant_name = tenant.name if tenant else "Unknown Store"
    
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=str(current_user.tenant_id),
        tenant_name=tenant_name
    )
