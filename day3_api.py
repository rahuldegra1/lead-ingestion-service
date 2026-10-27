from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import LeadDB, get_db, init_db

app = FastAPI(
    title="Persistent Lead Ingestion API",
    description="Pydantic v2 validation paired with SQLAlchemy & SQLite persistence.",
    version="1.0.0",
)

# Initialize database tables on server startup
init_db()


# 1. Incoming Request Schema (Sanitizes dirty inputs)
class LeadCreate(BaseModel):
    full_name: str
    email: str
    budget_inr: int = Field(gt=0, description="Budget in INR, must be greater than 0")
    phone: str

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().title()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def clean_and_validate_email(cls, value: str) -> str:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if "@" not in cleaned:
                raise ValueError("Invalid email: missing '@' symbol")
            return cleaned
        return value

    @field_validator("budget_inr", mode="before")
    @classmethod
    def clean_budget(cls, value):
        if isinstance(value, str):
            cleaned = value.replace("₹", "").replace(",", "").strip()
            return int(cleaned)
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        if isinstance(value, str):
            cleaned = value.replace("-", "").replace(" ", "").replace("+", "").strip()
            if not cleaned.isdigit() or len(cleaned) != 10:
                raise ValueError("Phone number must contain exactly 10 digits")
            return cleaned
        return value


# 2. Outgoing Response Schema (Includes database-generated ID)
class LeadResponse(BaseModel):
    id: int
    full_name: str
    email: str
    budget_inr: int
    phone: str

    class Config:
        from_attributes = True


# 3. Create and Persist a Lead
@app.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    # Convert validated Pydantic model into a SQLAlchemy ORM entity
    new_lead = LeadDB(**payload.model_dump())
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)  # Pull the auto-generated primary key ID
    return new_lead


# 4. Read All Persisted Leads
@app.get("/leads", response_model=list[LeadResponse], status_code=status.HTTP_200_OK)
def list_leads(db: Session = Depends(get_db)):
    leads = db.query(LeadDB).all()
    return leads


# 5. Read a Single Lead by ID
@app.get(
    "/leads/{lead_id}", response_model=LeadResponse, status_code=status.HTTP_200_OK
)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} does not exist",
        )
    return lead
