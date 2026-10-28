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
    # TODO (Lab 6): Look for a digit and for a unit token.
    raise NotImplementedError("Lab 6: implement is_measurable()")


def lint_decision(record: dict) -> list[str]:
    """A decision record that survives contact with reality. Problems (in this order) when any of
    "decision", "why", "gives_up", "alternatives" is missing or empty: "missing <key>"."""
    # TODO (Lab 6): One check per key.
    raise NotImplementedError("Lab 6: implement lint_decision()")


def route_feedback(reveals_missed_requirement: bool, conflicts_with_binding_constraint: bool) -> str:
    """"change_the_design" when the feedback reveals a requirement discovery missed; otherwise
    "explain_the_constraint" when it pushes against a tested binding constraint; otherwise
    "acknowledge_and_explain_the_trade_off"."""
    # TODO (Lab 6): Two ifs and a default.
    raise NotImplementedError("Lab 6: implement route_feedback()")


def summarize_for(audience: str, summary: dict, slos: SLOs, weak: list[str]) -> str:
    """One status, two framings. summary is evals.summarize() output; weak is evals.weak_strata().

    "executive": one line each for speed, cost, accuracy, routing and officer checks, in plain words with
                 MET / MISSED and the target; a final line naming weak areas if any. None of the JARGON
                 words may appear. Example: "Speed: 95% of case files are ready within 18 seconds
                 (target 60). MET"
    "technical": the same five metrics with their real names and numbers (p95_latency_s, avg_cost_usd,
                 field_accuracy, route_accuracy, review_rate) plus the weak strata list.
    Unknown audience -> ValueError."""
    # TODO (Lab 6): Build both framings from the overall block.
    raise NotImplementedError("Lab 6: implement summarize_for()")
