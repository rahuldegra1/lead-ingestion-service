from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import LeadDB, get_db, init_db
from day4_crud import LeadCreate, LeadResponse

app = FastAPI(
    title="Search & Paginated Lead API",
    description="Advanced querying, pagination, and multi-field filtering with FastAPI and SQLAlchemy.",
    version="1.0.0",
)

init_db()


# Paginated Response Wrapper with metadata
class PaginatedLeadResponse(BaseModel):
    total_count: int
    skip: int
    limit: int
    data: list[LeadResponse]


# ---------------------------------------------------------------------------
# Advanced Query Endpoint
# ---------------------------------------------------------------------------
@app.get("/leads", response_model=PaginatedLeadResponse, status_code=status.HTTP_200_OK)
def list_leads_filtered(
    skip: int = Query(
        default=0, ge=0, description="Number of records to skip (offset)"
    ),
    limit: int = Query(
        default=10, ge=1, le=100, description="Max records to return per page"
    ),
    min_budget: int | None = Query(
        default=None, ge=0, description="Filter leads with budget >= min_budget"
    ),
    max_budget: int | None = Query(
        default=None, ge=0, description="Filter leads with budget <= max_budget"
    ),
    search: str | None = Query(
        default=None,
        min_length=2,
        description="Case-insensitive search across name and email",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(LeadDB)

    # 1. Apply budget range filters if provided
    if min_budget is not None:
        query = query.filter(LeadDB.budget_inr >= min_budget)
    if max_budget is not None:
        query = query.filter(LeadDB.budget_inr <= max_budget)

    # 2. Apply text search across multiple fields
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                LeadDB.full_name.ilike(search_pattern),
                LeadDB.email.ilike(search_pattern),
            )
        )

    # 3. Calculate total matching records before applying pagination
    total_matching = query.count()

    # 4. Apply offset, limit, and sorting
    leads = query.order_by(LeadDB.budget_inr.desc()).offset(skip).limit(limit).all()

    return {"total_count": total_matching, "skip": skip, "limit": limit, "data": leads}


# Include existing CRUD endpoints for completeness
@app.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    new_lead = LeadDB(**payload.model_dump())
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    return new_lead


@app.get(
    "/leads/{lead_id}", response_model=LeadResponse, status_code=status.HTTP_200_OK
)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
    return lead
