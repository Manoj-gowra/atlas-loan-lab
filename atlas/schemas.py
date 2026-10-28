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
    application_id: str
    business_name: str
    customer_id: str
    loan_type: LoanType
    jurisdiction: Jurisdiction
    amount_requested: float
    term_months: int
    annual_revenue: float
    ebitda: float
    existing_annual_debt_service: float
    collateral_value: float
    years_in_business: float
    purpose: str
    submitted_on: date


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
