"""LAB 2 - Exercises 2.1 and 2.2: choosing the model tier and the deployment platform.

2.1 Selecting the Right Claude Model: three axes (capability, latency, cost). Pick "the cheapest,
    fastest model that reliably clears the quality bar the task actually needs, VERIFIED rather
    than assumed" - per task, never one tier for the whole system.
2.2 Deployment Platforms and Data Residency: the platform is an INHERITANCE decision (existing
    certifications, network boundaries, billing). Platform and model constrain each other: a model
    may reach a cloud marketplace later than the API, which you resolve deliberately and early.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskProfile:
    bounded: bool              # a well-defined transformation (extract, classify)?
    needs_judgment: bool       # weighing ambiguous or conflicting evidence?
    calls_per_day: int
    wrong_output_cost: str     # "low" | "high"
    person_waiting: bool       # is someone watching a screen for the answer?


def pick_tier(p: TaskProfile) -> str:
    """Return "haiku", "sonnet" or "opus".

    - bounded and no judgment needed                       -> "haiku" (high volume, cheap, fast)
    - judgment needed, high cost of a wrong answer, low volume (< 200 calls/day) and nobody
      waiting in real time                                 -> "opus"
    - everything else                                      -> "sonnet"
    Then VERIFY with an eval (Lab 4) - this function is the hypothesis, not the proof.
    """
    if p.bounded and not p.needs_judgment:
        return "haiku"
    if p.needs_judgment and p.wrong_output_cost == "high" and p.calls_per_day < 200 and not p.person_waiting:
        return "opus"
    return "sonnet"


@dataclass(frozen=True)
class Organization:
    cloud: str                       # "aws" | "gcp" | "none"
    certified_environment: bool      # data already lives in a compliance-reviewed cloud environment
    committed_spend: bool            # a committed-spend agreement with that cloud
    federal_fedramp_required: bool = False


MARKETPLACE = {"aws": "bedrock", "gcp": "vertex"}


def choose_platform(org: Organization) -> str:
    """Return "bedrock", "vertex" or "anthropic_api".

    Inherit what the organization already has: a certified environment or committed spend in AWS
    or GCP -> that cloud's marketplace offering. FedRAMP required but no AWS/GCP environment ->
    ValueError (a hard constraint you can't design around). Otherwise the Anthropic API.
    """
    if org.federal_fedramp_required and org.cloud not in MARKETPLACE:
        raise ValueError("FedRAMP is required: only an authorized cloud environment is usable")
    if (org.certified_environment or org.committed_spend or org.federal_fedramp_required) and org.cloud in MARKETPLACE:
        return MARKETPLACE[org.cloud]
    return "anthropic_api"


def availability_exceptions(component_models: dict[str, str], platform: str,
                            availability: dict[str, set[str]]) -> list[str]:
    """Components whose chosen model is NOT available on the platform yet, sorted.
    Each one needs a deliberate decision now (wait, change tier, or a documented exception) -
    not an improvised fix during deployment."""
    available = availability.get(platform, set())
    return sorted(c for c, m in component_models.items() if m not in available)
