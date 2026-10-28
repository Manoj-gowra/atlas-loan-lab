"""LAB 5 - Exercise 5.2: human-in-the-loop and escalation design.

Course lesson 5.2. Escalation is a deliberate design for CATEGORIES of decisions - not a net for
"whenever the model feels unsure". Four triggers:
  high_impact           - irreversible / high-stakes: an adverse action (decline) or a loan above the
                          loan officer's lending authority - regardless of how confident the system is
  policy_gap            - no written rule covers the case (the closest rule would be a guess)
  conflicting_evidence  - inputs disagree (stated vs verified EBITDA; specialists pulling opposite ways;
                          a citation that contradicts the rule applied - Lab 8)
  low_confidence        - uncertain fields, an escalated investigation, a tampered document
Every escalation carries an APPROVAL PACKET so the reviewer decides from evidence instead of
reconstructing the case. And watch the volume: too many escalations -> rubber-stamping.

Until you do Lab 5, the STARTER versions here return nothing so earlier labs run.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import capstone, config

TRIGGERS = ("high_impact", "policy_gap", "conflicting_evidence", "low_confidence")
LOAN_OFFICER_LIMIT = 500_000          # General Lending Standards 3.2
EBITDA_TOLERANCE = 0.10               # General Lending Standards 2.1


class ReviewQueue:
    """Given: a JSONL work queue (in production: the case-management system)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config.RUNS / "review_queue.jsonl")

    def add(self, app_id: str, queue: str, role: str, reason: str) -> dict:
        item = {"app_id": app_id, "queue": queue, "role": role, "reason": reason, "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(item) + "\n")
        return item

    def open_items(self, queue: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        items = [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
        return [i for i in items if i["status"] == "open" and (queue is None or i["queue"] == queue)]


def low_confidence_fields(confidence: dict[str, float], threshold: float = 0.8) -> list[str]:
    """Field names with confidence below the threshold, sorted."""
    return []  # TODO (Lab 5)


def escalation_triggers(case: Any) -> list[str]:
    """Which TRIGGERS apply to a CaseFile (return them in TRIGGERS order).

      high_impact:          case.recommendation == "decline", or the amount requested exceeds LOAN_OFFICER_LIMIT
      policy_gap:           "policy_gap" in case.flags
      conflicting_evidence: the financial_ratio metrics show verified_ebitda differing from stated_ebitda
                            by more than EBITDA_TOLERANCE (relative to stated); or
                            case.investigation.specialists_disagree; or
                            capstone.citation_conflicts(case.rule_report, case.explanation) is non-empty
      low_confidence:       case.review_fields or case.semantic_errors non-empty, or any of the flags
                            "agent_escalated", "citation_removed", "prompt_injection", "screening_unavailable",
                            "extraction_failed"
    Guard against missing pieces (no application, no investigation, no explanation).
    """
    return []  # TODO (Lab 5)


QUEUES: dict[str, tuple[str, str]] = {}  # TODO (Lab 5): trigger -> (queue name, role)


def required_authority(amount: float) -> str:
    """Given: who may sign this decision (General Lending Standards 3.2)."""
    if amount <= LOAN_OFFICER_LIMIT:
        return "loan_officer"
    return "senior_credit_officer" if amount <= 2_000_000 else "credit_committee"


def build_approval_packet(case: Any) -> dict[str, Any]:
    """Everything a reviewer needs to decide without reconstructing the case:
      {"app_id", "action": "approve or decline <app_id> for $<amount>", "required_authority",
       "triggers": case.triggers, "recommendation": case.recommendation,
       "evidence": [{"source": "rules_engine", "fact": detail, "policy": policy_ref} for each rule result]
                   + [{"source": f.source_specialist, "fact": f.finding} for each investigation finding],
       "unverified_asides": [{"source", "fact"} for each aside],
       "unable_to_check": investigation list or [],
       "reasoning": explanation text or "", "memo": case.memo}
    Return {} when the case has no application."""
    return {}  # TODO (Lab 5)


def route_to_queues(case: Any, queue: ReviewQueue) -> list[dict]:
    """Add one queue item per trigger in case.triggers using QUEUES; return the items."""
    return []  # TODO (Lab 5)


def rubber_stamp_risk(reviews: list[dict], min_reviews: int = 20) -> bool:
    """Calibration check. reviews: [{"agreed_with_system": bool, "seconds": float}, ...]. Risky when there
    are at least min_reviews, agreement is >= 98% AND the median review takes under 30 seconds."""
    # TODO (Lab 5): Three conditions; use statistics.median.
    raise NotImplementedError("Lab 5: implement rubber_stamp_risk()")
