"""LAB 4 - Exercise 4.3: diagnosing system failures.

Course lesson 4.3. A wrong output is a SYMPTOM. Three causes need three different fixes:
  prompt failure  - info was in context, the instruction was unclear  -> targeted prompt correction
  hallucination   - the needed info was NOT in context                -> grounding / retrieval, not "don't make things up"
  model mismatch  - info present, instruction clear, still fails      -> a more capable tier
Start with "what changed right before the regression?" - correlate timing before guessing.
And check STRUCTURAL validation (schema) separately from SEMANTIC validation (is it plausible?).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def diagnose(info_in_context: bool, instruction_clear: bool, fails_reliably: bool) -> str:
    """Return "retrieval_or_grounding", "prompt_failure", "model_mismatch" or "needs_more_evidence"
    (the course framework, in order: info present? instruction clear? fails reliably?)."""
    # TODO (Lab 4): Three ifs in order, then the fallback.
    raise NotImplementedError("Lab 4: implement diagnose()")


def semantic_checks(app: Any, today: date | None = None) -> list[str]:
    """Plausibility checks a schema can't express (structural pass != semantic pass):
      "EBITDA exceeds revenue"             if ebitda > annual_revenue
      "debt service exceeds revenue"       if existing_annual_debt_service > annual_revenue
      "no collateral value"                if collateral_value == 0
      "submitted in the future"            if submitted_on > today (default date(2026, 12, 31))
    Return the messages that apply, in this order."""
    return []  # TODO (Lab 4)


def what_changed(change_log: list[dict], regression_start: str, window_hours: int = 72) -> dict | None:
    """change_log: [{"ts": ISO datetime, "what": "..."}]. Return the LATEST change at or before
    regression_start and no more than window_hours earlier, or None."""
    # TODO (Lab 4): Parse with datetime.fromisoformat, filter to the window, take the max ts.
    raise NotImplementedError("Lab 4: implement what_changed()")
