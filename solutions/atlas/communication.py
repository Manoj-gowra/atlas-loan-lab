"""LAB 6 - Exercise 6.2: communicating architectural decisions and trade-offs.

Course lesson 6.2:
  - Same decision, two audiences: TECHNICAL wants mechanism; EXECUTIVE wants consequences in cost,
    risk and outcome. Translating is choosing which TRUE facts an audience needs, not losing substance.
  - Name every trade-off honestly: what it buys AND what it gives up.
  - Route feedback: a missed requirement changes the design; discomfort with a tested binding
    constraint gets a clear explanation - not a quiet concession to the loudest voice.
  - An SLA is MEASURABLE ("95% within 60 seconds"), never "fast and reliable".
"""
from __future__ import annotations

import re

from .design import SLOs

VAGUE_WORDS = ("fast", "quick", "reliable", "accurate enough", "robust", "scalable", "user-friendly", "good")
JARGON = ("token", "p95", "latency", "slo", "stratum", "strata", "cache", "embedding")


def is_measurable(statement: str) -> bool:
    """True when the statement contains a number AND a unit or percentage (%, second(s), minute(s),
    hour(s), $, cents, per cent). A vague word alone ("fast", "reliable") never makes it measurable."""
    has_number = bool(re.search(r"\d", statement))
    has_unit = bool(re.search(r"%|\$|\bcents?\b|\bper cent\b|\bseconds?\b|\bminutes?\b|\bhours?\b", statement, re.I))
    return has_number and has_unit


def lint_decision(record: dict) -> list[str]:
    """A decision record that survives contact with reality. Problems (in this order) when any of
    "decision", "why", "gives_up", "alternatives" is missing or empty: "missing <key>"."""
    return [f"missing {key}" for key in ("decision", "why", "gives_up", "alternatives") if not record.get(key)]


def route_feedback(reveals_missed_requirement: bool, conflicts_with_binding_constraint: bool) -> str:
    """"change_the_design" when the feedback reveals a requirement discovery missed; otherwise
    "explain_the_constraint" when it pushes against a tested binding constraint; otherwise
    "acknowledge_and_explain_the_trade_off"."""
    if reveals_missed_requirement:
        return "change_the_design"
    if conflicts_with_binding_constraint:
        return "explain_the_constraint"
    return "acknowledge_and_explain_the_trade_off"


def summarize_for(audience: str, summary: dict, slos: SLOs, weak: list[str]) -> str:
    """One status, two framings. summary is evals.summarize() output; weak is evals.weak_strata().

    "executive": one line each for speed, cost, accuracy, routing and officer checks, in plain words with
                 MET / MISSED and the target; a final line naming weak areas if any. None of the JARGON
                 words may appear. Example: "Speed: 95% of case files are ready within 18 seconds
                 (target 60). MET"
    "technical": the same five metrics with their real names and numbers (p95_latency_s, avg_cost_usd,
                 field_accuracy, route_accuracy, review_rate) plus the weak strata list.
    Unknown audience -> ValueError."""
    o = summary["overall"]
    met = {
        "speed": o["p95_latency_s"] <= slos.p95_case_ready_s, "cost": o["avg_cost_usd"] <= slos.max_avg_cost_usd,
        "accuracy": o["field_accuracy"] >= slos.min_field_accuracy, "routing": o["route_accuracy"] >= slos.min_route_accuracy,
        "checks": o["review_rate"] <= slos.max_review_rate,
    }
    word = {True: "MET", False: "MISSED"}
    if audience == "executive":
        lines = [
            f"Speed: 95% of case files are ready within {o['p95_latency_s']:.0f} seconds (target {slos.p95_case_ready_s:.0f}). {word[met['speed']]}",
            f"Running cost: ${o['avg_cost_usd']:.3f} per application on average (budget ${slos.max_avg_cost_usd:.2f}). {word[met['cost']]}",
            f"Accuracy: {o['field_accuracy']:.0%} of figures read correctly (target {slos.min_field_accuracy:.0%}). {word[met['accuracy']]}",
            f"Routing: {o['route_accuracy']:.0%} of applications sent down the right path (target {slos.min_route_accuracy:.0%}). {word[met['routing']]}",
            f"Officer checks: {o['review_rate']:.0%} of files need an officer to confirm a figure (limit {slos.max_review_rate:.0%}). {word[met['checks']]}",
        ]
        if weak:
            areas = ", ".join(w.split(":", 1)[1].replace("_", " ") for w in weak)
            lines.append(f"Watch: accuracy is below target for these application types: {areas}.")
        return "\n".join(lines)
    if audience == "technical":
        return "\n".join([
            f"p95_latency_s={o['p95_latency_s']} (<= {slos.p95_case_ready_s})",
            f"avg_cost_usd={o['avg_cost_usd']} (<= {slos.max_avg_cost_usd})",
            f"field_accuracy={o['field_accuracy']} (>= {slos.min_field_accuracy})",
            f"route_accuracy={o['route_accuracy']} (>= {slos.min_route_accuracy})",
            f"review_rate={o['review_rate']} (<= {slos.max_review_rate})",
            f"weak strata: {', '.join(weak) or 'none'}",
        ])
    raise ValueError(f"unknown audience {audience!r}")
