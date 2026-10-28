"""LAB 2 - Exercise 2.3 (tool layer): the data contract between the model and your code.

Lesson 2.3 instruction hierarchy: structural constraints belong in the TOOL SCHEMA, not in a
sentence asking the model to please comply. Two jobs at once:
  1. The schema is part of the prompt: field names, enums and descriptions guide the model.
  2. The schema is a guard: constraints reject impossible values in code (enforcement).
Notice what is NOT here: guarantor SSN, date of birth, home address (data minimisation, 5.3).
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

LoanType = Literal["term", "equipment", "ag_equipment", "cre"]
Jurisdiction = Literal["US-CA", "US-NY", "US-TX"]


class LoanApplication(BaseModel):
    application_id: str = Field(pattern=r"^APP-\d{3}$", description="Application ID, e.g. APP-001")
    business_name: str = Field(min_length=1, description="Legal name of the borrowing business")
    customer_id: str = Field(pattern=r"^B-\d{4}$", description="Business customer ID, e.g. B-1001")
    loan_type: LoanType
    jurisdiction: Jurisdiction = Field(description="State code of the lending jurisdiction, e.g. US-CA")
    amount_requested: float = Field(gt=0, le=10_000_000, description="Amount requested in USD as a plain number (180000, not '180k')")
    term_months: int = Field(ge=6, le=360, description="The term of THIS loan in months - not the remaining term of an existing lease or loan")
    annual_revenue: float = Field(ge=0, description="ANNUAL revenue in USD. Convert monthly (x12) or quarterly (x4) figures")
    ebitda: float = Field(ge=0, description="ANNUAL EBITDA in USD. Convert monthly (x12) or quarterly (x4) figures")
    existing_annual_debt_service: float = Field(ge=0, description="TOTAL annual payments on existing debts in USD: add every listed debt and annualise monthly payments (x12)")
    collateral_value: float = Field(ge=0, description="Appraised value of the collateral offered, USD")
    years_in_business: float = Field(ge=0, le=200, description="Years the business has operated; words to numbers; midpoint of a range")
    purpose: str = Field(description="Use of funds in a few words, or 'unspecified' if blank")
    submitted_on: date = Field(description="Submission date, YYYY-MM-DD")


class ExtractedApplication(LoanApplication):
    """What the extraction tool returns: the application plus per-field confidence (0-1)."""

    confidence: dict[str, float] = Field(description="Confidence from 0 to 1 for each field. Use below 0.8 when a "
                                                     "value is vague, inferred, missing or hard to read.")

    @field_validator("confidence")
    @classmethod
    def _in_range(cls, value: dict[str, float]) -> dict[str, float]:
        bad = {k: v for k, v in value.items() if not 0 <= v <= 1}
        if bad:
            raise ValueError(f"confidence values must be between 0 and 1: {bad}")
        return value
