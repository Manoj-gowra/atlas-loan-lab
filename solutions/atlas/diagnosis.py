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
    if not info_in_context:
        return "retrieval_or_grounding"
    if not instruction_clear:
        return "prompt_failure"
    if fails_reliably:
        return "model_mismatch"
    return "needs_more_evidence"


def semantic_checks(app: Any, today: date | None = None) -> list[str]:
    """Plausibility checks a schema can't express (structural pass != semantic pass):
      "EBITDA exceeds revenue"             if ebitda > annual_revenue
      "debt service exceeds revenue"       if existing_annual_debt_service > annual_revenue
      "no collateral value"                if collateral_value == 0
      "submitted in the future"            if submitted_on > today (default date(2026, 12, 31))
    Return the messages that apply, in this order."""
    today = today or date(2026, 12, 31)
    problems = []
    if app.ebitda > app.annual_revenue:
        problems.append("EBITDA exceeds revenue")
    if app.existing_annual_debt_service > app.annual_revenue:
        problems.append("debt service exceeds revenue")
    if app.collateral_value == 0:
        problems.append("no collateral value")
    if app.submitted_on > today:
        problems.append("submitted in the future")
    return problems


def what_changed(change_log: list[dict], regression_start: str, window_hours: int = 72) -> dict | None:
    """change_log: [{"ts": ISO datetime, "what": "..."}]. Return the LATEST change at or before
    regression_start and no more than window_hours earlier, or None."""
    start = datetime.fromisoformat(regression_start)
    window = [c for c in change_log
              if start - timedelta(hours=window_hours) <= datetime.fromisoformat(c["ts"]) <= start]
    return max(window, key=lambda c: datetime.fromisoformat(c["ts"])) if window else None
