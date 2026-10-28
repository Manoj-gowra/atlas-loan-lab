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
    # TODO (Lab 6): Check preference phrases first (an owner who 'prefers' is not stating a hard limit).
    raise NotImplementedError("Lab 6: implement classify_constraint()")


NEED_STATEMENT = "TODO: the need underneath 'an AI that reads loan documents'"

REQUIREMENTS: list[Requirement] = [
    # Requirement("R1", "Case file ready soon after upload", "p95 seconds from upload to case file", "<= 60"),
    # TODO: accuracy per document type, routing, review rate, cost, escalations with evidence
]

CONSTRAINTS: list[Constraint] = [
    # Constraint("C1", "Integrate with the current loan-origination platform", True, "<the owner's answer>"),
    # TODO: data residency, human decision, the dashboard, the language
]
