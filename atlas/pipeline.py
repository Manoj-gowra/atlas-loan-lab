"""The orchestrator: one application package in, one case file for an authorized person out.

GIVEN FILE - read it after Lab 1 and map it to the four-stage shape (lesson 1.4):
  INPUT       the uploaded package
  PROCESSING  input screening (5.1) -> intake, an augmented LLM (2.3) -> semantic checks (4.3)
              -> policy check, a workflow: rules in code (2.3) + retrieval and a cited explanation (3.3)
              -> ONLY if borderline: the coordinator and three specialist agents (1.3, 3.0)
              -> drafting (memo) -> output screening (5.1)
  OUTPUT      escalation triggers + approval packet (5.2): the human-in-the-loop REVIEW GATE
  FEEDBACK    officer corrections go to feedback.FeedbackStore (1.4) - captured in the UI, not here
Each step gets only the context it needs; the orchestrator owns the state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import data_access, diagnosis, escalation, guardrails, llm
from .agents import investigate
from .authz import DEFAULT_SESSION, CaseContext, Session
from .coordination import InvestigationResult
from .explain import Explanation, explain, gather_chunks
from .extraction import ExtractionFailed, extract
from .rag import PolicyIndex
from .rules import PolicyGap, RuleReport, check_application
from .schemas import LoanApplication
from .tracing import Trace, start_trace

INVESTIGATION_TO_DECISION = {"approve_with_conditions": "approve", "decline": "decline"}


@dataclass
class CaseFile:
    app_id: str
    status: str = "processing"   # "awaiting_officer_decision" | "needs_manual_intake"
    application: LoanApplication | None = None
    confidence: dict[str, float] = field(default_factory=dict)
    review_fields: list[str] = field(default_factory=list)
    semantic_errors: list[str] = field(default_factory=list)
    rule_report: RuleReport | None = None
    explanation: Explanation | None = None
    investigation: InvestigationResult | None = None
    memo: str = ""
    flags: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    packet: dict[str, Any] = field(default_factory=dict)
    trace: Trace | None = None

    @property
    def recommendation(self) -> str | None:
        """What the system suggests: "approve", "decline" or None (no automated suggestion)."""
        if self.rule_report is None or {"prompt_injection", "policy_gap", "screening_unavailable"} & set(self.flags):
            return None
        if self.rule_report.route != "investigate":
            return self.rule_report.route
        if self.investigation and self.investigation.status == "completed":
            return INVESTIGATION_TO_DECISION.get(self.investigation.recommendation)
        return None


def build_case_summary(case: CaseFile) -> dict[str, Any]:
    """Structured facts the memo writer may see. NOT here: the raw document, guarantor SSN, date of
    birth, home address, contact details (data minimisation, 5.3)."""
    report, inv = case.rule_report, case.investigation
    return {
        "application": case.application.model_dump(mode="json") if case.application else None,
        "route": report.route if report else None,
        "dscr": report.dscr if report else None,
        "ltv": report.ltv if report else None,
        "credit_score": report.credit_score if report else None,
        "rule_results": [r.__dict__ for r in report.results] if report else [],
        "explanation": case.explanation.text if case.explanation else "",
        "investigation": None if inv is None else {
            "status": inv.status, "recommendation": inv.recommendation, "reason": inv.reason,
            "findings": [f.__dict__ for f in inv.findings],
            "unverified_asides": [f.__dict__ for f in inv.unverified_asides],
            "unable_to_check": inv.unable_to_check},
        "review_fields": case.review_fields,
        "flags": case.flags,
    }


def draft_memo(case: CaseFile) -> str:
    summary = json.dumps(build_case_summary(case), indent=2, default=str)
    response = llm.call("drafting", [{"role": "user", "content": f"<case_summary>\n{summary}\n</case_summary>"}],
                        system=llm.build_system(llm.load_prompt("memo")), max_tokens=1500)
    return llm.text_of(response)


def _finish(case: CaseFile, trace: Trace, queue: Any) -> CaseFile:
    case.review_fields = escalation.low_confidence_fields(case.confidence)
    case.triggers = escalation.escalation_triggers(case)
    case.packet = escalation.build_approval_packet(case)
    escalation.route_to_queues(case, queue)
    if case.status == "processing":
        case.status = "awaiting_officer_decision"
    trace.save(redact=guardrails.redact_pii)
    return case


def process_application(app_id: str, session: Session = DEFAULT_SESSION, review_queue: Any = None,
                        prompt_name: str = "intake_v2", intake_model: str | None = None,
                        index: PolicyIndex | None = None) -> CaseFile:
    queue = review_queue if review_queue is not None else escalation.ReviewQueue()
    case = CaseFile(app_id=app_id)
    with start_trace(app_id) as trace:
        case.trace = trace
        raw = data_access.load_application_text(app_id)
        with trace.span("input_screening"):
            text, screen_flags = guardrails.screen_input(raw)
            case.flags.extend(screen_flags)
        try:
            with trace.span("intake"):
                result = extract(text, prompt_name, model=intake_model)
        except ExtractionFailed as exc:
            case.status = "needs_manual_intake"
            case.flags.append("extraction_failed")
            case.semantic_errors.append(str(exc))
            return _finish(case, trace, queue)
        app = case.application = result.application
        case.confidence = result.confidence
        case.semantic_errors = diagnosis.semantic_checks(app)
        if case.semantic_errors:
            case.flags.append("semantic_error")

        with trace.span("policy_check"):
            score = data_access.get_business_credit_report(app.customer_id)["score"]
            try:
                case.rule_report = check_application(app, score)
            except PolicyGap as gap:
                case.flags.append("policy_gap")
                case.semantic_errors.append(str(gap))
                return _finish(case, trace, queue)
            case.explanation = explain(app, case.rule_report, gather_chunks(app, case.rule_report, index=index))
            if case.explanation.flagged:
                case.flags.append("citation_removed")

        if case.rule_report.route == "investigate":
            ctx = CaseContext(app.application_id, app.customer_id, app.loan_type, app.jurisdiction,
                              app.submitted_on, session)
            case.investigation = investigate(app, case.rule_report, ctx)
            if case.investigation.status == "escalated":
                case.flags.append("agent_escalated")

        with trace.span("drafting"):
            case.memo = draft_memo(case)
            case.flags.extend(guardrails.screen_output(case.memo))
        return _finish(case, trace, queue)
