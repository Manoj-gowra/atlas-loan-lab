"""LAB 3 - Exercise 3.2: authentication, authorization and the tool-call gate.

Course lesson 3.2. Authentication answers WHO is calling; authorization answers WHAT that identity may
do - two separate checks. Authorization is enforced only at the DISPATCH / TOOL-CALL GATE, in code,
at the moment the action executes, against the caller's role and session scope - never by a prompt
("only access records for this applicant"), a UI restriction, or a caller's own claim.

Session scope: an AI acting for a loan officer must never see more than that officer can. Atlas
officers work a regional portfolio of jurisdictions, so the session carries that portfolio.

(Inside one process the component name stands in for an authenticated identity. In production each
component would authenticate with its OWN scoped credential, not one shared service account.)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .tools import GRANTS


@dataclass(frozen=True)
class Session:
    officer_id: str
    role: str                       # "loan_officer" | "senior_credit_officer" | "credit_committee"
    portfolio: frozenset[str]       # jurisdictions this officer may work on


DEFAULT_SESSION = Session("officer-17", "loan_officer", frozenset({"US-CA", "US-NY", "US-TX"}))


@dataclass(frozen=True)
class CaseContext:
    """Facts the SYSTEM fixes for every tool call in a case. The model cannot change them."""
    application_id: str
    customer_id: str
    loan_type: str
    jurisdiction: str
    as_of: date
    session: Session = DEFAULT_SESSION


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""


class AuthorizationUnavailable(Exception):
    """The authorization service could not be reached (simulated outage)."""


class AuthorizationService:
    def __init__(self) -> None:
        self.outage = False  # tests flip this to simulate an outage (lesson 5.1: fail secure)

    def check(self, component: str, tool: str, args: dict[str, Any], ctx: CaseContext) -> Decision:
        """Decide whether `component` may run `tool` with `args` in this case.

          1. tool not in GRANTS.get(component, ())                  -> deny "tool '<tool>' is not granted to <component>"
          2. args has a customer_id different from ctx.customer_id  -> deny "customer <id> is outside this case's scope"
          3. ctx.jurisdiction not in ctx.session.portfolio          -> deny "jurisdiction <j> is outside officer <id>'s portfolio"
          otherwise allow.
        (The outage check above this docstring's code is given.)"""
        if self.outage:
            raise AuthorizationUnavailable("authorization service did not respond")
        # TODO (Lab 3): Three deny checks in order, then allow.
        raise NotImplementedError("Lab 3: implement check()")


AUTHZ = AuthorizationService()
