"""LAB 3 - Exercise 3.5: accuracy-latency trade-offs, made deliberately per component.

Course lesson 3.5. "Fast and accurate" is not one goal. Five levers:
  model tier | STREAMING (perceived latency only - costs no accuracy, reach for it first) |
  batch vs synchronous (is anyone WAITING?) | retrieval depth | reasoning effort.
Choose the point that clears the accuracy bar the task needs inside its latency ceiling - and reject
a more accurate design that breaks the ceiling.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    mode: str                 # "synchronous" | "batch"
    streaming: bool
    retrieval_depth: int      # chunks per query (0 = no retrieval)
    reasoning: str            # "none" | "standard" | "deep"
    expected_latency_s: float


@dataclass(frozen=True)
class Requirement:
    person_waiting: bool
    latency_ceiling_s: float | None   # None = no real-time ceiling (a deadline, not a wait)


COMPONENT_PLANS: dict[str, Plan] = {
    "intake": Plan("synchronous", True, 0, "none", 2.0),
    "policy_check": Plan("synchronous", True, 2, "standard", 6.0),
    "investigation": Plan("synchronous", False, 4, "deep", 25.0),
    "nightly_rescoring": Plan("batch", False, 2, "standard", 3600.0),
}


def check_plan(plan: Plan, req: Requirement) -> list[str]:
    """Problems with a plan against its requirement (empty list = defensible):
      - batch while a person is waiting             -> "batch but someone is waiting"
      - synchronous with nobody waiting and no ceiling -> "nobody is waiting: consider batch"
      - a ceiling exists and expected latency exceeds it -> "breaks the latency ceiling" (no matter
        how much accuracy it buys)
      - a person waiting and not streaming          -> "stream the response"
    """
    problems = []
    if plan.mode == "batch" and req.person_waiting:
        problems.append("batch but someone is waiting")
    if plan.mode == "synchronous" and not req.person_waiting and req.latency_ceiling_s is None:
        problems.append("nobody is waiting: consider batch")
    if req.latency_ceiling_s is not None and plan.expected_latency_s > req.latency_ceiling_s:
        problems.append("breaks the latency ceiling")
    if req.person_waiting and not plan.streaming:
        problems.append("stream the response")
    return problems


def perceived_wait_s(time_to_first_token_s: float, total_s: float, streaming: bool) -> float:
    """What the person waiting feels: time to first token when streaming, the full time otherwise."""
    return time_to_first_token_s if streaming else total_s
