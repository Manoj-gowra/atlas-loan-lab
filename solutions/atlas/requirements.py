"""LAB 6 - Exercise 6.1: structured discovery and requirement gathering.

Course lesson 6.1:
  - A stakeholder states a WANT in solution language ("an AI that reads loan documents"); discovery
    finds the NEED underneath it ("what happens today without this? what does success look like in
    six months? who is hurt, and how?").
  - A REQUIREMENT is an outcome the system must deliver (checkable once built); a CONSTRAINT limits how.
  - Test every constraint: "what happens if this cannot be met?" - "revisit the whole approach" =
    BINDING; "we'd prefer it, but could work around it" = PREFERENCE.
  - Write it down as an artifact and validate it WITH the stakeholder (silence is not agreement).
Source: docs/discovery_notes.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    metric: str        # how you'd check it once built
    target: str


@dataclass(frozen=True)
class Constraint:
    id: str
    text: str
    binding: bool
    reason: str        # the stakeholder's answer that decided it


BINDING_PHRASES = ("revisit the whole", "cannot", "can't", "must not", "regulator", "law", "multi-year")
PREFERENCE_PHRASES = ("prefer", "nice to have", "work around", "would be fine", "equivalent")


def classify_constraint(answer: str) -> str:
    """The binding test, as code: "preference" if any PREFERENCE_PHRASES appear in the answer
    (lower-case), else "binding" if any BINDING_PHRASES appear, else "unclear" (ask again)."""
    text = answer.lower()
    if any(p in text for p in PREFERENCE_PHRASES):
        return "preference"
    if any(p in text for p in BINDING_PHRASES):
        return "binding"
    return "unclear"


NEED_STATEMENT = ("Cut the officer time spent on standard-case paperwork (retyping figures and looking up "
                  "policy) so officers can give borderline applications the judgment they need.")

REQUIREMENTS = [
    Requirement("R1", "Case file ready soon after upload", "p95 seconds from upload to case file", "<= 60"),
    Requirement("R2", "Extracted figures are trustworthy for every document type", "field accuracy per document type", ">= 0.95"),
    Requirement("R3", "Applications are routed correctly", "route accuracy", ">= 0.90"),
    Requirement("R4", "Few files need a manual field check", "share of applications with fields to review", "<= 0.30"),
    Requirement("R5", "Running cost stays within budget", "average model cost per application (USD)", "<= 0.05"),
    Requirement("R6", "Escalations reach the committee with evidence", "approval packets with evidence attached", "100%"),
]

CONSTRAINTS = [
    Constraint("C1", "Integrate with the current loan-origination platform", True,
               "replacing the LOS is a multi-year programme: we'd have to revisit the whole approach"),
    Constraint("C2", "Applicant data stays inside the bank's AWS account", True, "cannot: passed the regulator's cloud review"),
    Constraint("C3", "A person makes every credit decision", True, "cannot: policy 3.1 and fair-lending law"),
    Constraint("C4", "Show results in the Lending Hub dashboard", False, "prefers it; an equivalent view would be fine"),
    Constraint("C5", "Build it in Python", False, "nice to have; could work around it"),
]
