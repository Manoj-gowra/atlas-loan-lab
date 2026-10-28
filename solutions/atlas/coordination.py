"""LAB 1 - Exercise 1.3: coordinator and specialists, with provenance discipline.

Course lesson 1.3 (Multi-Agent Systems and Orchestration Strategy). Atlas's borderline-application
investigator is a COORDINATOR that dispatches three SPECIALISTS in parallel:
  financial_ratio   - recomputes the flagged figures (verified financials, bank activity)
  business_history  - repayment record, credit report, liens and public filings
  industry_risk     - sector conditions and sector-specific policy

Two habits the exam tests here:
  1. Scoped handoff: each specialist gets a SCOPED brief, not the full application or history.
  2. Provenance: every finding is attributed to the specialist that produced it (by the code that
     ran that specialist, not by what the text claims), and out-of-scope asides are labelled as
     unverified instead of being folded into the conclusion.

The agent loop that runs each specialist is Lab 3 (agents.py); here you write the parts that are
pure design: the brief and the synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SPECIALIST_SCOPES = {
    "financial_ratio": "cash flow, DSCR, verified financials and bank activity",
    "business_history": "repayment record, business credit report, liens, judgments and public filings",
    "industry_risk": "sector conditions and sector-specific policy",
}


@dataclass
class Finding:
    finding: str
    source_specialist: str
    in_scope: bool
    confidence: str             # "high" | "medium" | "low"
    unable_to_check: str | None = None


@dataclass
class SpecialistReport:
    specialist: str                     # which specialist session produced this (set by the coordinator)
    status: str                         # "completed" | "escalated"
    findings: list[dict] = field(default_factory=list)   # as submitted by the model
    recommendation: str = "inconclusive"                 # support_approval | support_decline | inconclusive
    reason: str = ""
    metrics: dict = field(default_factory=dict)          # structured numbers, e.g. verified vs stated EBITDA


@dataclass
class InvestigationResult:
    status: str                         # "completed" | "escalated"
    recommendation: str                 # approve_with_conditions | decline | refer_to_human
    findings: list[Finding] = field(default_factory=list)          # in scope, attributed
    unverified_asides: list[Finding] = field(default_factory=list)  # out of scope: label, don't absorb
    unable_to_check: list[str] = field(default_factory=list)
    specialists: dict[str, str] = field(default_factory=dict)       # role -> status
    recommendations: dict[str, str] = field(default_factory=dict)   # role -> that specialist's recommendation
    metrics: dict[str, dict] = field(default_factory=dict)          # role -> that specialist's metrics
    reason: str = ""

    @property
    def specialists_disagree(self) -> bool:
        """Given: True when some specialists supported approval and others supported decline."""
        return {"support_approval", "support_decline"} <= set(self.recommendations.values())


def format_brief(role: str, facts: dict[str, Any]) -> str:
    """Given: render a brief as 'key: value' lines (the specialists parse these)."""
    lines = [f"Specialist: {role}", f"Scope: {SPECIALIST_SCOPES[role]}"]
    for key, value in facts.items():
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        if isinstance(value, (int, float)) and key not in ("minimum DSCR", "DSCR", "LTV", "maximum LTV"):
            value = f"${value:,.0f}" if any(w in key for w in ("EBITDA", "debt service", "amount")) else value
        lines.append(f"{key}: {value}")
    lines.append("Investigate only within your scope. Report anything outside it as out of scope. "
                 "Finish by calling submit_findings.")
    return "\n".join(lines)


BRIEF_FIELDS: dict[str, list[str]] = {
    "financial_ratio": ["application_id", "customer_id", "flagged rules", "stated EBITDA",
                        "total annual debt service", "minimum DSCR", "LTV", "maximum LTV"],
    "business_history": ["application_id", "customer_id", "flagged rules", "years in business"],
    "industry_risk": ["application_id", "customer_id", "loan type", "jurisdiction"],
}


def specialist_brief(role: str, case_facts: dict[str, Any]) -> str:
    """A scoped handoff: format_brief(role, {only the BRIEF_FIELDS[role] keys present in case_facts}).
    Never pass the whole case: that reintroduces the context pollution the split was meant to stop."""
    scoped = {k: case_facts[k] for k in BRIEF_FIELDS[role] if k in case_facts}
    return format_brief(role, scoped)


def synthesize(reports: list[SpecialistReport]) -> InvestigationResult:
    """Combine specialist reports with provenance discipline.

    - Each submitted finding dict becomes a Finding whose source_specialist is report.specialist
      (ignore any source the dict itself claims).
    - in_scope False -> unverified_asides; in_scope True -> findings.
    - Every non-empty unable_to_check -> unable_to_check list, prefixed "<specialist>: ".
    - specialists maps role -> status; recommendations maps role -> recommendation; metrics maps
      role -> report.metrics.
    - Any escalated report -> status "escalated", recommendation "refer_to_human", reason naming who.
      Otherwise status "completed" and: any "support_decline" -> "decline"; else at least one
      "support_approval" -> "approve_with_conditions"; else (all inconclusive) -> "refer_to_human".
    """
    result = InvestigationResult(status="completed", recommendation="approve_with_conditions")
    for report in reports:
        result.specialists[report.specialist] = report.status
        result.recommendations[report.specialist] = report.recommendation
        result.metrics[report.specialist] = dict(report.metrics)
        for raw in report.findings:
            f = Finding(finding=str(raw.get("finding", "")), source_specialist=report.specialist,
                        in_scope=bool(raw.get("in_scope", False)), confidence=str(raw.get("confidence", "low")),
                        unable_to_check=raw.get("unable_to_check"))
            (result.findings if f.in_scope else result.unverified_asides).append(f)
            if f.unable_to_check:
                result.unable_to_check.append(f"{report.specialist}: {f.unable_to_check}")
    escalated = [r.specialist for r in reports if r.status == "escalated"]
    if escalated:
        result.status, result.recommendation = "escalated", "refer_to_human"
        result.reason = "specialists escalated: " + ", ".join(escalated)
    elif any(r.recommendation == "support_decline" for r in reports):
        result.recommendation = "decline"
    elif not any(r.recommendation == "support_approval" for r in reports):
        result.recommendation = "refer_to_human"
    return result
