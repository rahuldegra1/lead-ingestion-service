from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import verify_api_key
from app.database import get_db
from app.models.lead import LeadDB
from app.rate_limiter import limiter
from app.schemas.lead import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
    PaginatedLeadResponse,
)

router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_lead(
    request: Request,
    payload: LeadCreate,
    db: Session = Depends(get_db),
):
    new_lead = LeadDB(**payload.model_dump())
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead


@router.get("", response_model=PaginatedLeadResponse, status_code=status.HTTP_200_OK)
def list_leads(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    min_budget: int | None = Query(default=None, ge=0),
    max_budget: int | None = Query(default=None, ge=0),
    search: str | None = Query(default=None, min_length=2),
    db: Session = Depends(get_db),
):
    query = db.query(LeadDB)

    if min_budget is not None:
        query = query.filter(LeadDB.budget_inr >= min_budget)
    if max_budget is not None:
        query = query.filter(LeadDB.budget_inr <= max_budget)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                LeadDB.full_name.ilike(search_pattern),
                LeadDB.email.ilike(search_pattern),
            )
        )

    total_matching = query.count()
    leads = query.order_by(LeadDB.budget_inr.desc()).offset(skip).limit(limit).all()

    return {
        "total_count": total_matching,
        "skip": skip,
        "limit": limit,
        "data": leads,
    }


@router.get("/{lead_id}", response_model=LeadResponse, status_code=status.HTTP_200_OK)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse, status_code=status.HTTP_200_OK)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    db.delete(lead)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
