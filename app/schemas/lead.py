import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadBase(BaseModel):
    full_name: str
    email: str
    budget_inr: int = Field(gt=0, description="Budget in INR, must be positive")
    phone: str
    status: str = "NEW"

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
            # Extract only numeric digits, dropping currency symbols, commas, and encoding artifacts
            cleaned = re.sub(r"[^\d]", "", value)
            if not cleaned:
                raise ValueError("Budget must contain valid numeric digits")
            return int(cleaned)
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        if isinstance(value, str):
            cleaned = value.replace("-", "").replace(" ", "").replace("+", "").strip()
            if cleaned.startswith("91") and len(cleaned) == 12:
                cleaned = cleaned[2:]
            elif cleaned.startswith("0") and len(cleaned) == 11:
                cleaned = cleaned[1:]

            if not cleaned.isdigit() or len(cleaned) != 10:
                raise ValueError("Phone number must contain exactly 10 digits")
            return cleaned
        return value


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    budget_inr: int | None = Field(default=None, gt=0)
    phone: str | None = None
    status: str | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_name(cls, value):
        if isinstance(value, str):
            return value.strip().title()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
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
            cleaned = re.sub(r"[^\d]", "", value)
            if not cleaned:
                raise ValueError("Budget must contain valid numeric digits")
            return int(cleaned)
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value):
        if isinstance(value, str):
            cleaned = value.replace("-", "").replace(" ", "").replace("+", "").strip()
            if cleaned.startswith("91") and len(cleaned) == 12:
                cleaned = cleaned[2:]
            elif cleaned.startswith("0") and len(cleaned) == 11:
                cleaned = cleaned[1:]

            if not cleaned.isdigit() or len(cleaned) != 10:
                raise ValueError("Phone number must contain exactly 10 digits")
            return cleaned
        return value


class LeadResponse(LeadBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PaginatedLeadResponse(BaseModel):
    total_count: int
    skip: int
    limit: int
    data: list[LeadResponse]
