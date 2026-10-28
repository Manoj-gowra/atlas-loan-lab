"""LAB 5 - Exercise 5.3: compliance and ethical AI in practice.

Course lesson 5.3. Compliance constrains the architecture from the FIRST decision, not at a final
legal review:
  GDPR    (EU personal data)        -> data subject rights; limits on automated decisions with
                                       significant effects (meaningful human involvement)
  HIPAA   (US health information)   -> vendor agreement (BAA), audit trail, minimum necessary access
  FedRAMP (US federal cloud)        -> which deployment platforms are usable at all
Fairness is a SEPARATE obligation: a fully compliant system can still be biased. Stratify outcomes
by group (the aggregate hides disparity like it hides a weak document type) and watch PROXIES
such as ZIP codes and home addresses.
"""
from __future__ import annotations

import re
from collections import defaultdict

REGIMES: dict[str, set[str]] = {
    "GDPR": {"automated_decisions", "data_subject_rights"},
    "HIPAA": {"vendor_agreement", "audit_trail", "minimum_necessary_access"},
    "FedRAMP": {"deployment_platform"},
}


def regimes_constraining(aspect: str) -> list[str]:
    """Sorted names of the regimes in REGIMES that constrain this aspect."""
    return sorted(name for name, aspects in REGIMES.items() if aspect in aspects)


def approval_rates(decisions: list[dict], group_key: str = "group") -> dict[str, float]:
    """decisions: [{"group": "A", "approved": True}, ...] -> {group: approval rate, rounded to 4 decimals}."""
    totals, approved = defaultdict(int), defaultdict(int)
    for d in decisions:
        totals[d[group_key]] += 1
        approved[d[group_key]] += bool(d["approved"])
    return {g: round(approved[g] / totals[g], 4) for g in totals}


def adverse_impact_ratio(rates: dict[str, float]) -> float:
    """Lowest group rate / highest group rate (1.0 when there is one group or the highest is 0).
    Below 0.8 (the "four-fifths" screening heuristic) the disparity needs investigating - it is a
    signal for review, not a legal conclusion."""
    if len(rates) < 2 or max(rates.values()) == 0:
        return 1.0
    return round(min(rates.values()) / max(rates.values()), 4)


PROXY_PATTERNS = {"zip_code": r"\b\d{5}(?:-\d{4})?\b(?=\s*$|\s*[,.)])", "street_address": r"\b\d{2,5}\s+[A-Z][a-z]+\s+(?:St|Ave|Blvd|Rd|Dr|Ln)\b"}


def proxy_leaks(text_sent_to_model: str) -> list[str]:
    """Sorted PROXY_PATTERNS names found (multiline) in text that was sent to the model."""
    return sorted(name for name, p in PROXY_PATTERNS.items() if re.search(p, text_sent_to_model, re.M))
