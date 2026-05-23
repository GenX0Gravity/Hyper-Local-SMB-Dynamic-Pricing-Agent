from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from uuid import UUID
from backend.api.deps import get_db, get_current_tenant_id
from backend.models.product import Product

router = APIRouter()

# --- Request / Response Schemas ---
class ProductCreate(BaseModel):
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    cost_price: float = Field(gt=0)
    base_price: float = Field(gt=0)
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    stock_qty: int = Field(default=0, ge=0)

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, gt=0)
    base_price: Optional[float] = Field(default=None, gt=0)
    current_price: Optional[float] = Field(default=None, gt=0)
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    stock_qty: Optional[int] = Field(default=None, ge=0)

class ProductResponse(BaseModel):
    id: str
    sku: Optional[str]
    name: str
    description: Optional[str]
    category: Optional[str]
    cost_price: float
    base_price: float
    current_price: float
    max_price: Optional[float]
    min_price: Optional[float]
    stock_qty: int
    created_at: datetime
    updated_at: datetime

# --- Endpoints ---

@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    query = select(Product).where(Product.tenant_id == tenant_id)
    
    if category:
        query = query.where(Product.category == category)
    if search:
        query = query.where(
            Product.name.ilike(f"%{search}%") | 
            Product.sku.ilike(f"%{search}%")
        )
        
    products = db.exec(query).all()
    return products

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    # Enforce logic rules for pricing
    if payload.min_price is not None and payload.min_price < payload.cost_price:
        raise HTTPException(
            status_code=400,
            detail="Minimum price cannot be lower than cost price floor."
        )
        
    if payload.max_price is not None and payload.max_price < payload.base_price:
        raise HTTPException(
            status_code=400,
            detail="Maximum price cannot be lower than the base price baseline."
        )

    # Check for duplicate SKU
    if payload.sku:
        existing = db.exec(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.sku == payload.sku
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="A product with this SKU already exists.")

    product = Product(
        tenant_id=tenant_id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        cost_price=payload.cost_price,
        base_price=payload.base_price,
        current_price=payload.base_price, # Initial current price matches base
        max_price=payload.max_price,
        min_price=payload.min_price,
        stock_qty=payload.stock_qty
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("/{id}", response_model=ProductResponse)
def get_product(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    product = db.exec(
        select(Product).where(Product.tenant_id == tenant_id, Product.id == id)
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{id}", response_model=ProductResponse)
def update_product(
    id: UUID,
    payload: ProductUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    product = db.exec(
        select(Product).where(Product.tenant_id == tenant_id, Product.id == id)
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    
    # Enforce integrity checks if price variables are changing
    new_cost = update_data.get("cost_price", product.cost_price)
    new_base = update_data.get("base_price", product.base_price)
    new_min = update_data.get("min_price", product.min_price)
    new_max = update_data.get("max_price", product.max_price)
    new_current = update_data.get("current_price", product.current_price)

    if new_min is not None and new_min < new_cost:
        raise HTTPException(status_code=400, detail="Minimum price limit cannot fall below product cost floor.")
        
    if new_max is not None and new_max < new_base:
        raise HTTPException(status_code=400, detail="Maximum price limit cannot fall below base price baseline.")

    if new_current is not None:
        floor = new_min if new_min is not None else new_cost
        ceiling = new_max if new_max is not None else (new_base * 2.0)
        if new_current < floor or new_current > ceiling:
            raise HTTPException(
                status_code=400,
                detail=f"Price adjustment of {new_current} violates floor bounds ({floor}) or ceiling bounds ({ceiling})."
            )

    for key, value in update_data.items():
        setattr(product, key, value)
        
    product.updated_at = datetime.now(timezone.utc)
    
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    product = db.exec(
        select(Product).where(Product.tenant_id == tenant_id, Product.id == id)
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    db.commit()
    return
