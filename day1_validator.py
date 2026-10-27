import csv
import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator


class LeadRecord(BaseModel):
    full_name: str
    email: str
    budget_inr: int = Field(gt=0)
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


def process_leads_pipeline(
    input_path: str, clean_output_path: str, rejected_output_path: str
):
    clean_leads = []
    rejected_leads = []

    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: {input_path} not found.")
        return

    # 1. Stream and validate each row from the CSV
    with open(input_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):  # Header is line 1
            # Guard: check for unquoted comma overflows or missing columns
            if None in row:
                rejected_leads.append(
                    {
                        "csv_row": row_number,
                        "input_data": str(row),
                        "errors": [
                            "Malformed row: Extra columns detected (likely unquoted commas)"
                        ],
                    }
                )
                continue

            try:
                validated = LeadRecord(**row)
                clean_leads.append(validated.model_dump())
            except ValidationError as err:
                rejected_leads.append(
                    {
                        "csv_row": row_number,
                        "input_data": row,
                        "errors": [e["msg"] for e in err.errors()],
                    }
                )

    if clean_leads:
        with open(clean_output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["full_name", "email", "budget_inr", "phone"]
            )
            writer.writeheader()
            writer.writerows(clean_leads)

    if rejected_leads:
        with open(rejected_output_path, mode="w", encoding="utf-8") as f:
            json.dump(rejected_leads, f, indent=2)

    print("Processing complete:")
    print(f"  Valid records saved to '{clean_output_path}': {len(clean_leads)}")
    print(
        f"  Rejected records saved to '{rejected_output_path}': {len(rejected_leads)}"
    )


BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    process_leads_pipeline(
        input_path=BASE_DIR / "leads_input.csv",
        clean_output_path=BASE_DIR / "leads_clean.csv",
        rejected_output_path=BASE_DIR / "leads_rejected.json",
    )
