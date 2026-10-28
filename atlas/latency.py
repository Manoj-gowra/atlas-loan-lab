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
    # "intake": Plan(mode, streaming, retrieval_depth, reasoning, expected_latency_s),
    # TODO: intake, policy_check, investigation, nightly_rescoring
}


def check_plan(plan: Plan, req: Requirement) -> list[str]:
    """Problems with a plan against its requirement (empty list = defensible):
      - batch while a person is waiting             -> "batch but someone is waiting"
      - synchronous with nobody waiting and no ceiling -> "nobody is waiting: consider batch"
      - a ceiling exists and expected latency exceeds it -> "breaks the latency ceiling" (no matter
        how much accuracy it buys)
      - a person waiting and not streaming          -> "stream the response"
    """
    # TODO (Lab 3): Four independent checks, appending messages.
    raise NotImplementedError("Lab 3: implement check_plan()")


def perceived_wait_s(time_to_first_token_s: float, total_s: float, streaming: bool) -> float:
    """What the person waiting feels: time to first token when streaming, the full time otherwise."""
    # TODO (Lab 3): One conditional expression.
    raise NotImplementedError("Lab 3: implement perceived_wait_s()")
