"""LAB 2 - Exercise 2.3 (guidance is not enforcement): lending rules live in CODE.

Lesson 2.3: a prompt can STATE a rule ("never approve a disbursement over $500,000 without a second
reviewer") and the model will follow it most of the time. For anything where an occasional miss is
an unacceptable exposure, the rule must be checked programmatically at the point it matters. So the
DSCR, LTV and score thresholds are arithmetic in code: deterministic, testable, auditable. Claude
EXPLAINS the results (Lab 3, explain.py); it never decides whether 1.13 passes a 1.20 minimum.

This is the WORKFLOW's middle step (lesson 1.2): retrieve -> check rules in code -> explain.
Every result carries policy_ref, the chunk id of the section it enforces, so a decline can always
cite its reason (General Standards 1.2, adverse action).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .schemas import LoanApplication


@dataclass(frozen=True)
class ProductRules:
    loan_type: str
    policy_id: str
    version: int
    effective_from: date
    effective_to: date | None
    jurisdictions: tuple[str, ...]
    min_score: int
    min_dscr: float
    max_ltv: float
    min_amount: float
    max_amount: float
    apr: float
    min_years: float = 2
    score_margin: int = 15       # this far below min_score is "borderline"
    dscr_margin: float = 0.10    # this far below min_dscr is "borderline"
    ltv_margin: float = 0.05     # this far above max_ltv is "borderline"

    def ref(self, section: str) -> str:
        return f"{self.policy_id}-v{self.version}-{section}"


ALL = ("US-CA", "US-NY", "US-TX")
# Mirrors the policy documents. Policy and RULEBOOK change together (the policy-change skill, Lab 7).
RULEBOOK = [
    ProductRules("term", "POL-TERM", 3, date(2026, 1, 1), None, ALL, 160, 1.25, 0.80, 50_000, 1_000_000, 0.095),
    ProductRules("equipment", "POL-EQUIP", 3, date(2026, 1, 1), None, ALL, 155, 1.20, 0.85, 25_000, 2_000_000, 0.080),
    ProductRules("ag_equipment", "POL-AGEQ", 3, date(2026, 1, 1), date(2026, 10, 31), ("US-NY", "US-TX"), 155, 1.20, 0.80, 25_000, 1_500_000, 0.075),
    ProductRules("ag_equipment", "POL-AGEQ", 4, date(2026, 11, 1), None, ("US-NY", "US-TX"), 155, 1.35, 0.80, 25_000, 1_500_000, 0.075),
    ProductRules("cre", "POL-CRE", 3, date(2026, 1, 1), None, ALL, 165, 1.25, 0.75, 250_000, 5_000_000, 0.070),
    ProductRules("cre", "POL-CRE", 2, date(2024, 1, 1), date(2025, 12, 31), ALL, 160, 1.20, 0.80, 250_000, 4_000_000, 0.070),
]
# Stricter jurisdiction limits: (loan_type, jurisdiction) -> (rule field, value, section)
JURISDICTION_OVERRIDES = {("cre", "US-NY"): ("max_ltv", 0.70, "2.2")}


class PolicyGap(LookupError):
    """No written rule covers this product, jurisdiction and date (an escalation trigger, 5.2)."""


def rules_for(loan_type: str, jurisdiction: str, as_of: date) -> ProductRules:
    """Given: the rule set in force for this product, place and date."""
    for r in RULEBOOK:
        if r.loan_type == loan_type and r.effective_from <= as_of and (r.effective_to is None or as_of <= r.effective_to):
            if jurisdiction not in r.jurisdictions:
                raise PolicyGap(f"{r.policy_id} v{r.version} does not cover {jurisdiction}")
            return r
    raise PolicyGap(f"No {loan_type} policy in force on {as_of}")


def annual_payment(principal: float, apr: float, months: int) -> float:
    """Given: twelve amortised monthly payments."""
    r = apr / 12
    return 12 * principal * r / (1 - (1 + r) ** -months)


@dataclass
class RuleResult:
    rule_id: str        # "credit_score" | "dscr" | "ltv" | "loan_amount" | "time_in_business"
    status: str         # "pass" | "borderline" | "fail"
    value: float
    threshold: float
    policy_ref: str
    detail: str = ""


@dataclass
class RuleReport:
    application_id: str
    route: str          # "approve" | "decline" | "investigate"
    dscr: float
    ltv: float
    credit_score: int
    total_annual_debt_service: float
    rules_version: str
    results: list[RuleResult] = field(default_factory=list)

    @property
    def not_passed(self) -> list[RuleResult]:
        return [r for r in self.results if r.status != "pass"]

    def result(self, rule_id: str) -> RuleResult:
        return next(r for r in self.results if r.rule_id == rule_id)


# ------------------------------------------------------------------ LAB 2 TODOs


def compute_dscr(app: LoanApplication, rules: ProductRules) -> tuple[float, float]:
    """Return (dscr, total_annual_debt_service).
    total = existing_annual_debt_service + annual_payment(amount, rules.apr, term_months);
    dscr = ebitda / total, rounded to 3 decimals (0.0 if total is 0)."""
    # TODO (Lab 2): Implement the two formulas from policy section 1.2.
    raise NotImplementedError("Lab 2: implement compute_dscr()")


def _band_low(value: float, minimum: float, margin: float) -> str:
    return "pass" if value >= minimum else "borderline" if value >= minimum - margin else "fail"


def _band_high(value: float, maximum: float, margin: float) -> str:
    return "pass" if value <= maximum else "borderline" if value <= maximum + margin else "fail"


def check_application(app: LoanApplication, credit_score: int) -> RuleReport:
    """Run the five rules and decide the route (rules = rules_for(type, jurisdiction, submitted_on)).

      credit_score     _band_low(score, min_score, score_margin)                       section 1.1
      dscr             _band_low(dscr, min_dscr, dscr_margin)                          section 1.2
      loan_amount      fail outside [min_amount, max_amount], else pass                section 1.3
      ltv              amount / collateral (inf if no collateral); max_ltv may be
                       overridden by JURISDICTION_OVERRIDES (cite its section);
                       _band_high(ltv, max_ltv, ltv_margin)                            section 1.4
      time_in_business fail if years < min_years, else pass                            section 1.5
    Route: any fail -> "decline"; else any borderline -> "investigate"; else "approve".
    Use rules.ref(section) for policy_ref; round ltv to 3 decimals.
    """
    # TODO (Lab 2): Build the five RuleResults in the order above, then the route.
    raise NotImplementedError("Lab 2: implement check_application()")
