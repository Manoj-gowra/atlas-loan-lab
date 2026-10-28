"""LAB 3 - Exercise 3.0: the agent loop, and the coordinator that runs three specialists in parallel.

This is the investigator from lessons 1.2/1.3: an AGENT because where to look depends on what is
found, split into a coordinator and specialists because the subtasks are independent (signal 1)
and the full toolset would overload one agent (signal 2).

The loop, in one breath:
    call Claude with the specialist's own tools -> run EVERY tool_use through the gate -> send ALL
    results back in ONE user message (one tool_result per tool_use id) -> repeat until it calls
    submit_findings -> but STOP at a step or cost budget and escalate (lesson 5.1 risk controls).

The coordinator here is plain code (it always dispatches the same three roles - an enumerable
fan-out, i.e. a parallelization workflow around three agents). Its synthesis is yours from Lab 1.
"""
from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from . import llm
from .authz import CaseContext
from .coordination import InvestigationResult, SpecialistReport, specialist_brief, synthesize
from .gate import execute_tool
from .rules import RuleReport, rules_for
from .schemas import LoanApplication
from .tools import GRANTS, TERMINAL_TOOL, tool_defs
from .tracing import current_trace, start_trace, tagged

SPECIALISTS = ("financial_ratio", "business_history", "industry_risk")
VALID_RECOMMENDATIONS = {"support_approval", "support_decline", "inconclusive"}


def run_specialist(role: str, brief: str, ctx: CaseContext, max_steps: int = 5,
                   max_cost_usd: float = 0.40) -> SpecialistReport:
    """Run one specialist agent until it submits findings or a budget runs out.

    - tools = tool_defs(GRANTS[role]); system = llm.build_system(llm.load_prompt("specialist"))
    - messages start with {"role": "user", "content": brief}
    - each step: response = llm.call("investigation", messages, system=..., tools=..., max_tokens=2000);
      append {"role": "assistant", "content": llm.blocks_to_params(response.content)}
        * no tool calls                -> SpecialistReport(role, "escalated", reason="stopped without submitting findings")
        * a TERMINAL_TOOL call         -> validate input["recommendation"] in VALID_RECOMMENDATIONS
                                          (invalid -> escalated), else SpecialistReport(role, "completed",
                                          findings=input["findings"], recommendation=..., metrics=input.get("metrics") or {})
        * otherwise run EVERY tool_use: with trace.span(f"tool:{name}", kind="tool", component=role, args=input) as s:
              outcome = execute_tool(role, name, input, ctx); s.attrs.update(authorized=..., executed=..., is_error=...)
          and send ALL results in ONE user message:
              {"type": "tool_result", "tool_use_id": block.id, "content": outcome.content, "is_error": outcome.is_error}
    - after each step: if the cost this specialist has spent (trace llm spans tagged member=role) exceeds
      max_cost_usd -> escalated, reason mentions "cost budget"
    - steps used up -> escalated, reason mentions "step budget"
    Use current_trace() (the coordinator always runs you inside a trace).
    """
    # TODO (Lab 3): Implement the loop described above.
    raise NotImplementedError("Lab 3: implement run_specialist()")


# ------------------------------------------------------------------ given: the coordinator


def case_facts(app: LoanApplication, report: RuleReport) -> dict[str, Any]:
    """Every fact the coordinator could hand over. specialist_brief() picks a scoped subset."""
    rules = rules_for(app.loan_type, app.jurisdiction, app.submitted_on)
    ltv = report.result("ltv")
    return {
        "application_id": app.application_id, "customer_id": app.customer_id, "business name": app.business_name,
        "loan type": app.loan_type, "jurisdiction": app.jurisdiction, "amount requested": app.amount_requested,
        "flagged rules": ", ".join(f"{r.rule_id} {r.status} ({r.detail})" for r in report.not_passed) or "none",
        "stated EBITDA": app.ebitda, "total annual debt service": report.total_annual_debt_service,
        "minimum DSCR": rules.min_dscr, "DSCR": report.dscr, "LTV": ltv.value, "maximum LTV": ltv.threshold,
        "years in business": app.years_in_business, "annual revenue": app.annual_revenue,
        "purpose": app.purpose,
    }


def _run_member(role: str, brief: str, ctx: CaseContext, **budgets: Any) -> SpecialistReport:
    with tagged(member=role):
        return run_specialist(role, brief, ctx, **budgets)


def investigate(app: LoanApplication, report: RuleReport, ctx: CaseContext, **budgets: Any) -> InvestigationResult:
    """Coordinator: scoped briefs out, three specialists in parallel, attributed synthesis back."""
    trace = current_trace()
    if trace is None:  # standalone use (tests): open a trace so budgets and spans still work
        with start_trace(f"investigation-{app.application_id}"):
            return investigate(app, report, ctx, **budgets)
    facts = case_facts(app, report)
    with tagged(group="investigation"):
        with ThreadPoolExecutor(max_workers=len(SPECIALISTS)) as pool:
            futures = [pool.submit(contextvars.copy_context().run, _run_member, role,
                                   specialist_brief(role, facts), ctx, **budgets) for role in SPECIALISTS]
            reports = [f.result() for f in futures]
    return synthesize(reports)
