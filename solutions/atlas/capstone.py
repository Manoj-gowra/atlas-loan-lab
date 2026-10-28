"""LAB 8 - The capstone (course Chapter 8, Cross-Domain Scenario).

Case 2 - the near-miss regression: two weeks after a policy update, agricultural equipment
explanations cite a threshold that no longer matches current policy. The dashboard average looks
fine; a loan officer catches it just before credit committee. The course's fix list ends with:
"update the escalation-trigger definitions so a citation that far out of step with current policy
gets caught automatically." That is citation_conflicts(), which escalation.py already calls.

Case 1 - the renewals request: "an AI system like the one you already built, but for renewals."
A pattern that worked once is a hypothesis for the next case. RENEWALS_DESIGN is your answer.
"""
from __future__ import annotations

from typing import Any


def _split(ref: str) -> tuple[str, int, str]:
    """Given: "POL-AGEQ-v4-1.2" -> ("POL-AGEQ", 4, "1.2")."""
    head, section = ref.rsplit("-", 1)
    policy, version = head.rsplit("-v", 1)
    return policy, int(version), section


def citation_conflicts(report: Any, explanation: Any) -> list[dict]:
    """Citations that point at a DIFFERENT VERSION of the same policy section a rule was checked against.

    For each rule result in report.results and each citation in explanation.citations: same policy id and
    same section but a different version -> {"rule_id", "applied": rule.policy_ref, "cited": citation}.
    That is exactly what a stale index produces: the rules engine applies v4 while the explanation quotes v3.
    """
    conflicts = []
    for rule in report.results:
        r_pol, r_ver, r_sec = _split(rule.policy_ref)
        for cited in explanation.citations:
            c_pol, c_ver, c_sec = _split(cited)
            if (c_pol, c_sec) == (r_pol, r_sec) and c_ver != r_ver:
                conflicts.append({"rule_id": rule.rule_id, "applied": rule.policy_ref, "cited": cited})
    return conflicts


RENEWALS_DESIGN: dict[str, Any] = {
    "need": "cut time to decision for the routine majority of renewals before quarter-end",
    "pattern_routine": "workflow",
    "pattern_flagged": "agent",
    "flag_signals": ["covenant violation", "significant revenue drop", "missing required document"],
    "model_routine": "haiku",
    "model_flagged": "opus",
    "reuse_origination_index": False,        # renewal policy has legacy versions: build a fresh index on the canonical policy
    "reuse_origination_eval_set": False,     # build a renewals dataset stratified standard vs flagged
    "eval_strata": ["standard", "flagged"],
    "reuse_escalation_definitions": False,   # the four triggers apply; what counts as each is renewal-specific
    "tell_the_vp": "a leaner workflow for routine renewals plus a narrow investigator path, cheaper than a copy",
}
