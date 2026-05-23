"""Dynamic Pricing Engine API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.api.deps import get_current_tenant_id, get_db
from backend.services.dynamic_pricing.schemas import DynamicPricingReport
from backend.services.dynamic_pricing.service import dynamic_pricing_service

router = APIRouter()


class EvaluatePricingRequest(BaseModel):
    demand_score: Optional[float] = Field(
        None, ge=0, le=100, description="Override demand score (else forecast/heuristic)"
    )
    persist: bool = Field(True, description="Save recommendations to database")


@router.post("/evaluate", response_model=DynamicPricingReport)
async def evaluate_dynamic_pricing(
    body: EvaluatePricingRequest | None = None,
    persist: bool = Query(True),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Run the full dynamic pricing algorithm for all products.

    Inputs: demand score, inventory, event score, weather score, business rules.
    Outputs: discount %, price increase %, bundle offers, happy hour campaigns.
    Every recommendation includes a full explanation.
    """
    req = body or EvaluatePricingRequest()
    try:
        return await dynamic_pricing_service.evaluate_tenant(
            db,
            tenant_id,
            demand_score=req.demand_score,
            persist=req.persist if body else persist,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/report", response_model=DynamicPricingReport)
async def get_pricing_report(
    demand_score: Optional[float] = Query(None, ge=0, le=100),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Dry-run pricing report without persisting recommendations."""
    try:
        return await dynamic_pricing_service.evaluate_tenant(
            db,
            tenant_id,
            demand_score=demand_score,
            persist=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
