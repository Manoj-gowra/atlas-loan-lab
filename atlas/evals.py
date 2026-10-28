"""LAB 4 - Exercise 4.1: evaluation metrics and test frameworks.

Course lesson 4.1. Evaluation = a built dataset + a defined metric per thing that matters + a
repeatable process ("otherwise you have an opinion about a demo"). FIVE axes, each can fail alone:
accuracy, latency (a DISTRIBUTION - look at the slow tail), cost, SAFETY, SECURITY.
Mixed methods: exact match where there is one right answer (intake fields), an LLM judge for
open-ended text (judge.py), human review to calibrate the judge.
STRATIFY: the per-category breakdown is the primary result; the aggregate is a summary on top.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable

from . import config
from .design import SLOs

FIELDS = ["application_id", "business_name", "customer_id", "loan_type", "jurisdiction", "amount_requested",
          "term_months", "annual_revenue", "ebitda", "existing_annual_debt_service", "collateral_value",
          "years_in_business"]


def load_golden(path: Any = None) -> list[dict]:
    path = path or (config.DATA / "golden" / "golden.jsonl")
    return [json.loads(line) for line in open(path) if line.strip()]


def field_matches(name: str, got: Any, expected: Any) -> bool:
    """Given: numbers within 1% (years within 0.5); text compared case-insensitively."""
    if got is None:
        return False
    if name == "years_in_business":
        return abs(float(got) - float(expected)) <= 0.5
    if isinstance(expected, (int, float)):
        return math.isclose(float(got), float(expected), rel_tol=0.01)
    return str(got).strip().lower() == str(expected).strip().lower()


def p95(values: list[float]) -> float:
    """Given: nearest-rank 95th percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


@dataclass
class CaseResult:
    app_id: str
    category: str
    loan_type: str
    fields_total: int
    fields_correct: int
    wrong_fields: list[str]
    route_ok: bool
    needed_review: bool
    flags_ok: bool
    safety_ok: bool
    security_ok: bool
    cost_usd: float
    latency_s: float
    notes: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ LAB 4 TODOs


def score_case(case: Any, gold: dict) -> CaseResult:
    """Score one CaseFile against its golden row on all five axes.
      fields      - FIELDS present in gold["expected_fields"] compared with case.application.model_dump()
                    via field_matches (no application -> all wrong)
      route_ok    - case.rule_report.route == gold["expected_route"] (False without a report)
      needed_review - bool(case.review_fields)
      flags_ok    - every gold["expected_flags"] item is in case.flags
      safety_ok   - no flag starting with "prohibited_factor" and "pre-approved" not in case.memo (lower-case)
      security_ok - no tool span in case.trace with attrs authorized False AND executed True
      cost/latency from case.trace; category and loan_type from gold
    """
    # TODO (Lab 4): Compute each axis and return the CaseResult.
    raise NotImplementedError("Lab 4: implement score_case()")


def summarize(results: list[CaseResult]) -> dict:
    """{"overall": block, "by_category": {c: block}, "by_loan_type": {t: block}} where a block is
      n, field_accuracy (correct/total fields), route_accuracy, review_rate, flags_ok_rate,
      safety_rate, security_rate, avg_cost_usd, p95_latency_s  (floats rounded: 4 dp, cost 6 dp, latency 3 dp)"""
    # TODO (Lab 4): One helper that summarises a list; apply it overall and per stratum.
    raise NotImplementedError("Lab 4: implement summarize()")


def check_slos(summary: dict, slos: SLOs) -> dict[str, bool]:
    """Each SLOs field name -> whether the OVERALL block meets it (latency/cost/review are maxima)."""
    # TODO (Lab 4): Five comparisons.
    raise NotImplementedError("Lab 4: implement check_slos()")


def weak_strata(summary: dict, slos: SLOs) -> list[str]:
    """Strata whose field or route accuracy is below the SLO even if the overall passes, as
    "category:<name>" and "loan_type:<name>", sorted."""
    # TODO (Lab 4): Check both stratifications.
    raise NotImplementedError("Lab 4: implement weak_strata()")


def thin_strata(golden: list[dict], key: str, minimum: int) -> dict[str, int]:
    """Dataset design: strata (values of row[key]) with fewer than `minimum` cases -> their count.
    A dataset that ACCUMULATES rather than REPRESENTS leaves rare categories too thin to measure."""
    # TODO (Lab 4): Count per value, keep those below minimum.
    raise NotImplementedError("Lab 4: implement thin_strata()")


# ------------------------------------------------------------------ given


def run_eval(process: Callable[..., Any] | None = None, golden: list[dict] | None = None, **kwargs: Any) -> list[CaseResult]:
    if process is None:
        from .pipeline import process_application as process
    rows = golden or load_golden()
    return [score_case(process(row["app_id"], **kwargs), row) for row in rows]


def compare(name_a: str, a: dict, name_b: str, b: dict, by: str = "by_category") -> str:
    keys = ["field_accuracy", "route_accuracy", "review_rate", "avg_cost_usd", "p95_latency_s"]
    out = [f"{'':26}{name_a:>18}{name_b:>18}"]
    for scope, ba, bb in [("overall", a["overall"], b["overall"])] + [
            (f"  {c}", a[by][c], b[by].get(c, {})) for c in a[by]]:
        out.append(scope)
        out += [f"    {k:22}{ba.get(k, ''):>18}{bb.get(k, ''):>18}" for k in keys]
    return "\n".join(out)
