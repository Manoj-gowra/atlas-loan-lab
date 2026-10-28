"""LAB 3 - Integration (course Chapter 3): agents, least privilege, the gate, RAG, protocols,
latency and observability.

    pytest tests/test_lab3.py [--solution]
Guide: docs/LAB3.md. Needs Labs 1-2 (synthesis, briefs, model routing, extraction, rules).
"""
import asyncio
import importlib.util
import shutil
from datetime import date

import pytest
from _helpers import app_from_gold, fake_client, process

from atlas import config, data_access
from atlas.agents import case_facts, investigate, run_specialist
from atlas.authz import AUTHZ, DEFAULT_SESSION, CaseContext, Session
from atlas.coordination import specialist_brief
from atlas.rules import check_application
from atlas.tracing import start_trace, tagged


def borderline(app_id):
    app = app_from_gold(app_id)
    report = check_application(app, data_access.get_business_credit_report(app.customer_id)["score"])
    ctx = CaseContext(app.application_id, app.customer_id, app.loan_type, app.jurisdiction, app.submitted_on)
    return app, report, ctx


def run_one(role, app_id, **budgets):
    app, report, ctx = borderline(app_id)
    with start_trace(f"{app_id}-{role}") as trace, tagged(member=role):
        result = run_specialist(role, specialist_brief(role, case_facts(app, report)), ctx, **budgets)
    return result, trace


# ====================================================================== 3.0 The agent loop (lessons 1.2/1.3 built)


def test_3_0_specialist_runs_tools_retries_once_and_submits():
    report, trace = run_one("financial_ratio", "APP-006")
    assert report.status == "completed", report.reason
    assert report.metrics["verified_ebitda"] == 236000 and report.metrics["stated_ebitda"] == 190000
    tools = [(s.name, s.attrs["is_error"]) for s in trace.tool_calls()]
    assert tools == [("tool:get_verified_financials", False), ("tool:get_bank_statements", True),
                     ("tool:get_bank_statements", False)], "both tool_uses run; the timed-out one is retried once"
    assert all(s.attrs["component"] == "financial_ratio" for s in trace.tool_calls())


def test_3_0_out_of_scope_lookup_is_denied_and_reported():
    report, trace = run_one("business_history", "APP-006")
    denied = [s for s in trace.tool_calls() if s.attrs["args"].get("customer_id") == "B-1012"]
    assert denied and denied[0].attrs["authorized"] is False and denied[0].attrs["executed"] is False
    assert report.status == "completed"
    assert any("B-1012" in (f.get("unable_to_check") or "") for f in report.findings)


def test_3_0_step_budget_stops_a_looping_agent():
    report, trace = run_one("business_history", "APP-007", max_steps=4)
    assert report.status == "escalated" and "step budget" in report.reason
    assert len(trace.llm_calls()) == 4


def test_3_0_cost_budget_stops_an_expensive_agent():
    report, trace = run_one("financial_ratio", "APP-006", max_cost_usd=0.0001)
    assert report.status == "escalated" and "cost budget" in report.reason
    assert len(trace.llm_calls()) == 1


def test_3_0_coordinator_runs_three_specialists_in_parallel():
    app, report, ctx = borderline("APP-006")
    with start_trace("APP-006") as trace:
        result = investigate(app, report, ctx)
    assert result.status == "completed" and result.recommendation == "approve_with_conditions"
    assert set(result.specialists) == {"financial_ratio", "business_history", "industry_risk"}
    members = {s.attrs.get("member") for s in trace.llm_calls()}
    assert members == {"financial_ratio", "business_history", "industry_risk"}
    serial = sum(s.latency_s for s in trace.spans if s.kind in ("llm", "tool"))
    assert trace.latency_s < serial, "parallel specialists: the case waits for the slowest, not the sum"
    assert [a.source_specialist for a in result.unverified_asides] == ["financial_ratio"]


# ====================================================================== 3.1 Capability bloat, least privilege
from atlas.tools import GRANTS, LEGACY_REGISTRY, READ_ONLY, TERMINAL_TOOL, WRITE, audit_grants  # noqa: E402

COMPONENTS = ("intake", "explainer", "drafting", "financial_ratio", "business_history", "industry_risk", "approval_gate")


def test_3_1_every_component_has_a_deliberate_grant():
    assert set(GRANTS) == set(COMPONENTS)
    assert GRANTS["intake"] == GRANTS["explainer"] == GRANTS["drafting"] == frozenset()
    assert GRANTS["approval_gate"] == frozenset({"update_application_status"})


def test_3_1_nobody_gets_the_legacy_tool_and_only_the_gate_writes():
    assert set(GRANTS) == set(COMPONENTS), "grant deliberately, component by component"
    for component, tools in GRANTS.items():
        assert "manage_loan_record" not in tools, "split the broad tool; nobody receives the old one"
        if component != "approval_gate":
            assert not tools & WRITE, f"{component} must not hold a write tool"


def test_3_1_specialists_get_small_toolsets_of_their_own():
    for role in ("financial_ratio", "business_history", "industry_risk"):
        tools = GRANTS[role]
        assert TERMINAL_TOOL in tools and len(tools) <= 5
        assert tools - {TERMINAL_TOOL} <= READ_ONLY
    assert not GRANTS["financial_ratio"] & GRANTS["business_history"] - {TERMINAL_TOOL}


def test_3_1_audit_applies_the_four_questions():
    findings = audit_grants("intake", set(LEGACY_REGISTRY), needed=set(), inherited=set(LEGACY_REGISTRY))
    assert [f["tool"] for f in findings] == sorted(LEGACY_REGISTRY), "intake needs none of the shared registry"
    by_tool = {f["tool"]: f["reasons"] for f in findings}
    assert by_tool["manage_loan_record"] == ["not required by the current task",
                                             "inherited from a shared default, not deliberately granted",
                                             "misuse would be disproportionate to this component's scope"]
    assert by_tool["get_industry_risk"] == ["not required by the current task",
                                            "inherited from a shared default, not deliberately granted"]
    gate = audit_grants("approval_gate", {"update_application_status"}, needed={"update_application_status"}, inherited=set())
    assert gate == [], "a needed, deliberate, proportionate grant is kept"


def test_3_1_intake_is_sent_no_data_tools():
    process("APP-001")
    intake_calls = [c for c in fake_client().calls if "record_application" in c["tools"]]
    assert intake_calls and all(c["tools"] == ["record_application"] for c in intake_calls)


# ====================================================================== 3.2 AuthN vs AuthZ, the tool-call gate
from atlas.gate import execute_tool  # noqa: E402

CTX = CaseContext("APP-006", "B-1006", "equipment", "US-CA", date(2026, 9, 29))


def test_3_2_authorization_checks_grant_then_scope_then_portfolio():
    allowed = AUTHZ.check("business_history", "get_public_filings", {"customer_id": "B-1006"}, CTX)
    assert allowed.allowed
    no_grant = AUTHZ.check("intake", "update_application_status", {"application_id": "APP-006"}, CTX)
    assert not no_grant.allowed and "not granted to intake" in no_grant.reason
    other = AUTHZ.check("business_history", "get_business_credit_report", {"customer_id": "B-1012"}, CTX)
    assert not other.allowed and "B-1012" in other.reason
    ca_only = CaseContext("APP-004", "B-1004", "equipment", "US-NY", date(2026, 10, 2),
                          Session("officer-3", "loan_officer", frozenset({"US-CA"})))
    portfolio = AUTHZ.check("industry_risk", "get_industry_risk", {"customer_id": "B-1004"}, ca_only)
    assert not portfolio.allowed and "portfolio" in portfolio.reason


def test_3_2_the_gate_never_executes_an_unauthorized_call():
    out = execute_tool("drafting", "manage_loan_record", {"action": "disburse", "application_id": "APP-006", "amount": 9e6}, CTX)
    assert (out.is_error, out.authorized, out.executed) == (True, False, False)
    assert out.content.startswith("Not authorized")
    assert data_access.read_disbursements() == [] and data_access.read_statuses() == {}


def test_3_2_the_gate_turns_failures_into_results():
    ok = execute_tool("industry_risk", "get_industry_risk", {"customer_id": "B-1006"}, CTX)
    assert (ok.is_error, ok.authorized, ok.executed) == (False, True, True) and '"sector"' in ok.content
    flaky = execute_tool("financial_ratio", "get_bank_statements", {"customer_id": "B-1006"}, CTX)
    assert flaky.is_error and flaky.executed and "retry" in flaky.content.lower()
    bad = execute_tool("financial_ratio", "get_bank_statements", {}, CTX)
    assert bad.is_error and bad.content.startswith("Error")
    terminal = execute_tool("financial_ratio", TERMINAL_TOOL, {"findings": [], "recommendation": "inconclusive"}, CTX)
    assert terminal.is_error and terminal.authorized and not terminal.executed


def test_3_2_an_authorization_outage_fails_secure(monkeypatch):
    monkeypatch.setattr(AUTHZ, "outage", True)
    out = execute_tool("industry_risk", "get_industry_risk", {"customer_id": "B-1006"}, CTX)
    assert (out.is_error, out.authorized, out.executed) == (True, False, False)
    assert "fail secure" in out.content


def test_3_2_the_session_never_sees_more_than_its_officer():
    ca_officer = Session("officer-3", "loan_officer", frozenset({"US-CA"}))
    case = process("APP-009", session=ca_officer)  # a New York application
    assert case.investigation is not None
    assert not any(s.attrs.get("executed") for s in case.trace.tool_calls()), "every look-up is out of portfolio"
    assert case.investigation.unable_to_check and case.recommendation is None
    assert DEFAULT_SESSION.portfolio == frozenset({"US-CA", "US-NY", "US-TX"})


# ====================================================================== 3.3 Chunking, indexing, retrieval
from atlas import rag  # noqa: E402
from atlas.explain import build_messages, explain, gather_chunks, invalid_citations  # noqa: E402

POLICIES = config.DATA / "policies"


def test_3_3_one_chunk_per_numbered_rule():
    chunks = rag.chunk_policy(POLICIES / "equipment_v3.md")
    assert [c.id for c in chunks] == ["POL-EQUIP-v3-1.1", "POL-EQUIP-v3-1.2", "POL-EQUIP-v3-1.3", "POL-EQUIP-v3-1.4",
                                      "POL-EQUIP-v3-1.5", "POL-EQUIP-v3-2.1", "POL-EQUIP-v3-2.2", "POL-EQUIP-v3-2.3"]
    dscr = chunks[1]
    assert dscr.heading_path == "Equipment Financing Policy (v3) > 1. Eligibility > 1.2 Debt service coverage ratio"
    assert dscr.text.startswith("1.2 Debt service coverage ratio\n") and "1.10 to 1.19 is borderline" in dscr.text, \
        "the exception in the second sentence stays with its rule"
    assert (dscr.loan_type, dscr.version, dscr.section, dscr.effective_to) == ("equipment", 3, "1.2", None)
    assert dscr.jurisdictions == ["US-CA", "US-NY", "US-TX"]


def test_3_3_metadata_filter():
    chunks = {c.id: c for c in rag.chunk_policy(POLICIES / "cre_v2.md") + rag.chunk_policy(POLICIES / "general_v1.md")}
    old, general = chunks["POL-CRE-v2-1.2"], chunks["POL-GEN-v1-1.1"]
    assert rag.is_applicable(old, "cre", "US-NY", date(2025, 3, 1))
    assert not rag.is_applicable(old, "cre", "US-NY", date(2026, 3, 1)), "superseded version"
    assert not rag.is_applicable(old, "term", "US-NY", date(2025, 3, 1)), "other product"
    assert rag.is_applicable(general, "equipment", "US-TX", date(2026, 3, 1)), "'all' applies to every product"
    ag = rag.chunk_policy(POLICIES / "ag_equipment_v3.md")[0]
    assert not rag.is_applicable(ag, "ag_equipment", "US-CA", date(2026, 3, 1)), "jurisdiction not covered"


def test_3_3_filter_first_then_rank():
    index = rag.PolicyIndex.build(POLICIES)
    hits = rag.retrieve("debt service coverage ratio DSCR minimum", "equipment", "US-CA", date(2026, 9, 1), k=3, index=index)
    assert hits[0].id == "POL-EQUIP-v3-1.2"
    assert all(h.policy_id in ("POL-EQUIP", "POL-GEN") for h in hits), "never another product's threshold"
    cre = rag.retrieve("debt service coverage ratio DSCR minimum", "cre", "US-NY", date(2026, 9, 1), k=4, index=index)
    assert cre and all(c.version == 3 for c in cre if c.policy_id == "POL-CRE"), "never a superseded version"
    assert rag.retrieve("zzz qqq", "term", "US-CA", date(2026, 9, 1), index=index) == [], "zero scores are dropped"


def test_3_3_index_records_what_it_was_built_from(tmp_path):
    folder = tmp_path / "policies"
    shutil.copytree(POLICIES, folder)
    index = rag.PolicyIndex.build(folder)
    assert set(index.fingerprints) == {p.name for p in folder.glob("*.md")}
    assert index.ranker_version == rag.RANKER_VERSION and index.built_at
    assert not index.is_stale(folder)
    assert index.is_stale(folder, ranker_version="bm25-v2"), "a new ranker/embedding model = reindex"
    (folder / "term_v3.md").write_text((folder / "term_v3.md").read_text().replace("1.25", "1.30"))
    assert index.is_stale(folder), "source changed, index not rebuilt = stale"
    fresh = rag.PolicyIndex.build(folder)
    (folder / "extra.md").write_text((folder / "term_v3.md").read_text())
    assert fresh.is_stale(folder), "a new policy file also makes it stale"


def test_3_3_explanation_messages_keep_per_request_content_in_the_user_turn():
    app, report, _ = borderline("APP-006")
    chunks = gather_chunks(app, report)
    msgs = build_messages(app, report, chunks)
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    assert content.index("<application_facts>") < content.index("<rule_results") < content.index("<policy_chunk")
    assert 'route="investigate"' in content


def test_3_3_invented_citations_are_detected_named_and_retried():
    app, report, _ = borderline("APP-006")
    chunks = gather_chunks(app, report)
    assert invalid_citations("ok [POL-EQUIP-v3-1.2] bad [POL-GEN-v1-4.2]", {"POL-EQUIP-v3-1.2"}) == ["POL-GEN-v1-4.2"]
    exp = explain(app, report, chunks)
    assert exp.attempts == 2 and not exp.flagged
    assert set(exp.citations) <= {c.id for c in chunks} and exp.chunk_ids == [c.id for c in chunks]
    assert "POL-GEN-v1-4.2" in fake_client().calls[-1]["all_text"], "the retry NAMES the invalid citation"


def test_3_3_a_persistent_hallucination_is_stripped_and_flagged():
    app, report, _ = borderline("APP-006")
    exp = explain(app, report, gather_chunks(app, report), max_attempts=1)
    assert exp.flagged and exp.removed_citations == ["POL-GEN-v1-4.2"]
    assert "[POL-GEN-v1-4.2]" not in exp.text and "[citation removed: not in retrieved policy]" in exp.text


# ====================================================================== 3.4 Protocols: MCP, API, agent-to-agent
from atlas.protocols import choose_protocol, select_tools  # noqa: E402


def test_3_4_choose_protocol():
    assert choose_protocol(single_stable_connection=True) == "direct_api"          # intake's document service
    assert choose_protocol(reused_or_evolving=True) == "mcp"                       # bureaus and public records
    assert choose_protocol(autonomous_external_peer=True, reused_or_evolving=True) == "agent_to_agent"  # partner bank
    with pytest.raises(ValueError):
        choose_protocol()


def test_3_4_progressive_discovery_loads_only_what_the_task_needs():
    catalog = {"get_public_filings": "UCC liens, tax liens and judgments", "get_industry_risk": "sector stress",
               "get_bank_statements": "monthly deposits and NSF events", "send_email": "email a customer",
               "get_business_credit_report": "business credit score, liens, judgments"}
    assert select_tools({"liens", "judgments"}, catalog) == ["get_business_credit_report", "get_public_filings"]
    assert select_tools({"nsf", "deposits", "sector"}, catalog, limit=1) == ["get_bank_statements"]
    assert select_tools({"weather"}, catalog) == []


needs_mcp = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="pip install 'mcp>=2.2,<3'")


@needs_mcp
def test_3_4_mcp_server_exposes_only_what_each_client_needs():
    from atlas.mcp_bridge import list_tools_async
    from atlas.mcp_server import CLIENT_EXPOSURE, SOURCES, build_server
    assert CLIENT_EXPOSURE["investigator"] == set(SOURCES)
    assert CLIENT_EXPOSURE["analyst_desktop"] == {"get_industry_risk"}
    assert "get_verified_financials" not in CLIENT_EXPOSURE["claude_code"] and CLIENT_EXPOSURE["claude_code"]
    for client, exposed in CLIENT_EXPOSURE.items():
        tools = asyncio.run(list_tools_async(build_server(client)))
        assert {t["name"] for t in tools} == exposed
        assert all(t["read_only"] for t in tools), "annotate every tool with readOnlyHint"


@needs_mcp
def test_3_4_mcp_tools_plug_into_the_messages_api():
    from atlas.mcp_bridge import call_tool, claude_tool_defs
    from atlas.mcp_server import build_server
    server = build_server("investigator")
    defs = claude_tool_defs(server)
    assert defs and all(set(d) == {"name", "description", "input_schema"} for d in defs)
    out = call_tool(server, "get_industry_risk", {"customer_id": "B-1009"})
    assert not out.is_error and "stress_index" in out.content


# ====================================================================== 3.5 Accuracy-latency trade-offs
from atlas.latency import COMPONENT_PLANS, Plan, Requirement, check_plan, perceived_wait_s  # noqa: E402

REQUIREMENTS = {
    "intake": Requirement(person_waiting=True, latency_ceiling_s=10),
    "policy_check": Requirement(person_waiting=True, latency_ceiling_s=30),
    "investigation": Requirement(person_waiting=False, latency_ceiling_s=60),
    "nightly_rescoring": Requirement(person_waiting=False, latency_ceiling_s=None),
}


def test_3_5_every_component_plan_is_defensible():
    assert set(COMPONENT_PLANS) == set(REQUIREMENTS)
    for name, plan in COMPONENT_PLANS.items():
        assert check_plan(plan, REQUIREMENTS[name]) == [], name


def test_3_5_levers_differ_by_component():
    p = COMPONENT_PLANS
    assert p["intake"].streaming and p["intake"].retrieval_depth == 0 and p["intake"].reasoning == "none"
    assert p["investigation"].reasoning == "deep" and p["investigation"].retrieval_depth > p["policy_check"].retrieval_depth
    assert p["nightly_rescoring"].mode == "batch"


def test_3_5_check_plan_rejects_accuracy_past_the_ceiling():
    slow_but_accurate = Plan("synchronous", True, 0, "deep", 14.0)
    assert check_plan(slow_but_accurate, REQUIREMENTS["intake"]) == ["breaks the latency ceiling"]
    assert check_plan(Plan("batch", False, 0, "none", 2.0), REQUIREMENTS["intake"]) == \
           ["batch but someone is waiting", "stream the response"]
    assert check_plan(Plan("synchronous", False, 2, "standard", 600), REQUIREMENTS["nightly_rescoring"]) == \
           ["nobody is waiting: consider batch"]


def test_3_5_streaming_changes_perceived_latency_only():
    assert perceived_wait_s(0.8, 6.0, streaming=True) == 0.8
    assert perceived_wait_s(0.8, 6.0, streaming=False) == 6.0


# ====================================================================== 3.6 Observability and monitoring
from atlas.feedback import FeedbackStore  # noqa: E402
from atlas.monitoring import ALERTS, cache_hit_rate, evaluate_alerts, should_close_ticket, stratify  # noqa: E402


def test_3_6_a_trace_captures_what_llm_systems_need():
    case = process("APP-006")
    t = case.trace
    llm_spans = t.llm_calls()
    assert {s.attrs["task"] for s in llm_spans} >= {"intake", "policy_check", "investigation", "drafting"}
    assert all(s.attrs["model"] and s.attrs["cache"] in ("hit", "write", "none") for s in llm_spans)
    assert t.retrievals() and all(r.attrs["chunk_ids"] for r in t.retrievals()), "which chunks came back"
    assert [s.name for s in t.tool_calls()], "which tools ran, in what order"
    assert t.cost_usd > 0 and t.latency_s > 0
    assert (config.RUNS / "traces" / "APP-006.jsonl").exists()


def test_3_6_cache_hit_rate_across_cases():
    cases = [process(a) for a in ("APP-001", "APP-002", "APP-005")]
    assert cache_hit_rate([c.trace for c in cases], "policy_check") > 0.5
    assert cache_hit_rate([c.trace for c in cases], "no_such_task") == 0.0


def test_3_6_stratify_reveals_what_the_average_hides():
    rows = [("pdf", 1.0)] * 9 + [("handwritten", 0.0)]
    by_format = stratify(rows, key=lambda r: r[0], value=lambda r: r[1])
    assert by_format == {"pdf": 1.0, "handwritten": 0.0}


def test_3_6_alerts_fire_on_signals_that_move():
    base = {"correction_rate_by_field": {"ebitda": 0.03}, "cache_hit_rate": 0.8, "cost_per_call": 0.01}
    calm = {"correction_rate_by_field": {"ebitda": 0.04, "term_months": 0.03}, "cache_hit_rate": 0.7, "cost_per_call": 0.012}
    assert evaluate_alerts(calm, base) == []
    bad = {"correction_rate_by_field": {"ebitda": 0.03, "dscr": 0.09}, "cache_hit_rate": 0.2, "cost_per_call": 0.03}
    assert evaluate_alerts(bad, base) == list(ALERTS)
    assert evaluate_alerts({}, base) == []


def test_3_6_correction_rate_per_field_is_a_live_signal():
    store = FeedbackStore()
    for app in ("APP-001", "APP-002", "APP-003"):
        store.record(app, "intake", "extraction", "ebitda", 1, 2, "officer-17")
    store.record("APP-004", "intake", "extraction", "term_months", 36, 60, "officer-17")
    assert store.correction_rate_by_field(cases_reviewed=20) == {"ebitda": 0.15, "term_months": 0.05}
    assert store.correction_rate_by_field(cases_reviewed=0) == {}


def test_3_6_a_clean_retry_does_not_close_a_quality_ticket():
    assert should_close_ticket(True, 0)
    assert not should_close_ticket(True, 3), "non-determinism: a pattern of similar reports"
    assert not should_close_ticket(False, 0)


# ====================================================================== the whole Integrate stage, end to end


def test_3_end_to_end_borderline_case():
    case = process("APP-006")
    assert case.rule_report.route == "investigate"
    assert case.explanation.citations and not case.explanation.flagged
    inv = case.investigation
    assert inv.status == "completed" and case.recommendation == "approve"
    assert all(f.source_specialist in ("financial_ratio", "business_history", "industry_risk") for f in inv.findings)
    assert any("B-1012" in u for u in inv.unable_to_check)
    assert "UNVERIFIED" in case.memo
