"""LAB 3 - Exercise 3.1: capability bloat and least privilege in tool configuration.

Course lesson 3.1. Capability bloat = access beyond the CURRENT task. It accumulates quietly: a tool
left over after a scope change, a shared registry where every agent got every tool, a broad tool
whose description keeps growing "do not use this to..." warnings. Least privilege REMOVES the
capability - logging it (detective) or confirming it (compensating) leaves the exposure in place.

LEGACY_REGISTRY below is what every component used to receive by default, including the broad
`manage_loan_record` tool. Your job: grant each component only what its task needs (GRANTS), and
write the audit that would have caught the bloat (audit_grants).
"""
from __future__ import annotations

import json
from typing import Any, Callable

from . import data_access

TERMINAL_TOOL = "submit_findings"

TOOL_DEFS: dict[str, dict] = {
    "get_verified_financials": {
        "name": "get_verified_financials",
        "description": "Read-only. Tax-return verified revenue and EBITDA for a business customer.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    "get_bank_statements": {
        "name": "get_bank_statements",
        "description": "Read-only. Monthly deposits, ending balance and NSF count for the last N months (max 12).",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"},
                                                          "months": {"type": "integer", "minimum": 1, "maximum": 12}},
                         "required": ["customer_id"]}},
    "get_business_credit_report": {
        "name": "get_business_credit_report",
        "description": "Read-only. Business credit bureau report: score (0-300), days beyond terms, liens, judgments.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    "get_public_filings": {
        "name": "get_public_filings",
        "description": "Read-only. UCC liens, tax liens and judgments filed in the last N years.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"},
                                                          "years": {"type": "integer", "minimum": 1}},
                         "required": ["customer_id"]}},
    "get_industry_risk": {
        "name": "get_industry_risk",
        "description": "Read-only. Sector, NAICS code, sector stress index (0-100) and outlook for a customer.",
        "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    "search_policy": {
        "name": "search_policy",
        "description": "Read-only. Search the lending policy in force for THIS case (product, jurisdiction and date are "
                       "fixed by the system). Returns matching sections with their ids.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    "update_application_status": {
        "name": "update_application_status",
        "description": "WRITE. Sets an application's official status. Only the approval gate uses this.",
        "input_schema": {"type": "object", "properties": {"application_id": {"type": "string"}, "status": {"type": "string"},
                                                          "note": {"type": "string"}}, "required": ["application_id", "status"]}},
    "manage_loan_record": {
        "name": "manage_loan_record",
        "description": "LEGACY. Read a loan record, update its status, or disburse funds. Do not use this to update a "
                       "status without officer approval. Do not use this to disburse without a second reviewer. Do not "
                       "use the disburse action for amounts over $500,000. Do not use this for read-only requests "
                       "without setting action=read.",
        "input_schema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["read", "update_status", "disburse"]},
                                                          "application_id": {"type": "string"}, "amount": {"type": "number"}},
                         "required": ["action", "application_id"]}},
    TERMINAL_TOOL: {
        "name": TERMINAL_TOOL,
        "description": "Call exactly once to hand your findings to the coordinator. Ends your investigation.",
        "input_schema": {"type": "object", "properties": {
            "findings": {"type": "array", "items": {"type": "object", "properties": {
                "finding": {"type": "string"}, "in_scope": {"type": "boolean"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "unable_to_check": {"type": ["string", "null"]}}, "required": ["finding", "in_scope", "confidence"]}},
            "recommendation": {"type": "string", "enum": ["support_approval", "support_decline", "inconclusive"]},
            "metrics": {"type": "object", "description": "Optional structured numbers you computed, e.g. "
                                                         "{\"verified_ebitda\": 236000, \"stated_ebitda\": 190000}"}},
            "required": ["findings", "recommendation"]}},
}

READ_ONLY = frozenset({"get_verified_financials", "get_bank_statements", "get_business_credit_report",
                       "get_public_filings", "get_industry_risk", "search_policy"})
WRITE = frozenset({"update_application_status", "manage_loan_record"})
LEGACY_REGISTRY = frozenset(TOOL_DEFS)  # the old shared default: every component got everything

GRANTS: dict[str, frozenset[str]] = {
    # TODO: one entry per component: intake, explainer, drafting, financial_ratio, business_history,
    # industry_risk, approval_gate. Today every component effectively has LEGACY_REGISTRY.
}


def tool_defs(names: frozenset[str] | set[str]) -> list[dict]:
    """Given: API tool definitions for these names, in a stable order (stable = cache friendly)."""
    return [TOOL_DEFS[n] for n in TOOL_DEFS if n in names]


def audit_grants(component: str, granted: set[str], needed: set[str], inherited: set[str]) -> list[dict]:
    """The course's four audit questions, as code. For each granted tool (sorted by name) collect reasons:
      - not in `needed`                                   -> "not required by the current task"
      - in `inherited`                                    -> "inherited from a shared default, not deliberately granted"
      - in WRITE and component != "approval_gate"         -> "misuse would be disproportionate to this component's scope"
    A tool that is needed, not inherited and not disproportionate has no reasons and is kept.
    Return [{"tool": name, "reasons": [...]}, ...] for tools with at least one reason (remove them)."""
    # TODO (Lab 3): Loop over sorted(granted), build the reasons list, keep entries with reasons.
    raise NotImplementedError("Lab 3: implement audit_grants()")


# ------------------------------------------------------------------ given: implementations behind the gate

def _search_policy(args: dict, ctx: Any) -> dict:
    from .rag import retrieve
    chunks = retrieve(str(args["query"]), ctx.loan_type, ctx.jurisdiction, ctx.as_of, k=3)
    return {"sections": [{"id": c.id, "text": c.text} for c in chunks]}


IMPLEMENTATIONS: dict[str, Callable[[dict, Any], Any]] = {
    "get_verified_financials": lambda a, c: data_access.get_verified_financials(a["customer_id"]),
    "get_bank_statements": lambda a, c: data_access.get_bank_statements(a["customer_id"], int(a.get("months", 6))),
    "get_business_credit_report": lambda a, c: data_access.get_business_credit_report(a["customer_id"]),
    "get_public_filings": lambda a, c: data_access.get_public_filings(a["customer_id"], int(a.get("years", 3))),
    "get_industry_risk": lambda a, c: data_access.get_industry_risk(a["customer_id"]),
    "search_policy": _search_policy,
    "update_application_status": lambda a, c: data_access.update_application_status(a["application_id"], a["status"], a.get("note", "")),
    "manage_loan_record": lambda a, c: (data_access.disburse_funds(a["application_id"], float(a.get("amount", 0)))
                                        if a.get("action") == "disburse"
                                        else data_access.update_application_status(a["application_id"], "updated")
                                        if a.get("action") == "update_status" else {"record": a["application_id"]}),
}


def to_json(obj: Any) -> str:
    return json.dumps(obj, default=str)
