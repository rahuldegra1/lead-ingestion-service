from fastapi import FastAPI, status
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Lead Ingestion API",
    description="Mircoservice demonstring Pydantic v2 request validation in FastAPI. ",
    version="1.0.0",
)


class LeadRecord(BaseModel):
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


# 2. Health check route
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "lead-ingestion"}


# 3. Single Lead Ingestion (Returns 201 Created on success, 422 automatically on invalid data)
@app.post("/leads", status_code=status.HTTP_201_CREATED)
async def create_lead(lead: LeadRecord):
    # FastAPI automatically validates and cleans the payload before reaching this line
    return {"message": "Lead accepted and sanitized", "data": lead.model_dump()}


# 4. Batch Lead Ingestion
@app.post("/leads/batch", status_code=status.HTTP_201_CREATED)
async def create_leads_batch(leads: list[LeadRecord]):
    return {
        "message": f"Successfully ingested {len(leads)} leads",
        "data": [lead.model_dump() for lead in leads],
    }
