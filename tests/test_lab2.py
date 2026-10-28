"""LAB 2 - Models, prompting and context engineering (course Chapter 2).

    pytest tests/test_lab2.py [--solution]
Guide: docs/LAB2.md. Needs Lab 1 (TASK_DESIGN drives model routing).
"""
from datetime import date

import pytest
from _helpers import app_from_gold, fake_client, gold, usage
from pydantic import ValidationError

from atlas import config, data_access, llm
from atlas.tracing import start_trace

# ====================================================================== 2.1 Selecting the right model
from atlas.selection import Organization, TaskProfile, availability_exceptions, choose_platform, pick_tier


@pytest.mark.parametrize("profile, tier", [
    (TaskProfile(bounded=True, needs_judgment=False, calls_per_day=400, wrong_output_cost="low", person_waiting=True), "haiku"),
    (TaskProfile(bounded=False, needs_judgment=True, calls_per_day=20, wrong_output_cost="high", person_waiting=False), "opus"),
    (TaskProfile(bounded=False, needs_judgment=True, calls_per_day=400, wrong_output_cost="low", person_waiting=True), "sonnet"),
    # high stakes, but someone is watching the screen: the latency budget rules out the slowest tier
    (TaskProfile(bounded=False, needs_judgment=True, calls_per_day=20, wrong_output_cost="high", person_waiting=True), "sonnet"),
    # high stakes but high volume: not the most capable tier for every call
    (TaskProfile(bounded=False, needs_judgment=True, calls_per_day=5000, wrong_output_cost="high", person_waiting=False), "sonnet"),
])
def test_2_1_pick_tier_per_task(profile, tier):
    assert pick_tier(profile) == tier


def test_2_1_choose_model_routes_each_task_to_its_own_tier():
    assert llm.choose_model("intake") == config.MODELS["haiku"]
    assert llm.choose_model("policy_check") == config.MODELS["sonnet"]
    assert llm.choose_model("investigation") == config.MODELS["opus"]
    assert llm.choose_model("judge") == config.MODELS["sonnet"]


def test_2_1_no_model_for_human_or_unknown_tasks():
    with pytest.raises(ValueError):
        llm.choose_model("decision")
    with pytest.raises(ValueError):
        llm.choose_model("make_coffee")


# ====================================================================== 2.2 Platforms and data residency


def test_2_2_platform_is_inherited():
    assert choose_platform(Organization("aws", certified_environment=True, committed_spend=False)) == "bedrock"
    assert choose_platform(Organization("gcp", certified_environment=False, committed_spend=True)) == "vertex"
    assert choose_platform(Organization("none", certified_environment=False, committed_spend=False)) == "anthropic_api"
    # nothing to inherit: the most restrictive option is not automatically required
    assert choose_platform(Organization("aws", certified_environment=False, committed_spend=False)) == "anthropic_api"


def test_2_2_fedramp_is_a_hard_constraint():
    assert choose_platform(Organization("aws", False, False, federal_fedramp_required=True)) == "bedrock"
    with pytest.raises(ValueError):
        choose_platform(Organization("none", False, False, federal_fedramp_required=True))


def test_2_2_model_availability_exceptions_are_decided_early():
    components = {"intake": "haiku", "policy_check": "sonnet", "investigation": "opus"}
    availability = {"bedrock": {"haiku", "sonnet"}, "anthropic_api": {"haiku", "sonnet", "opus"}}
    assert availability_exceptions(components, "bedrock", availability) == ["investigation"]
    assert availability_exceptions(components, "anthropic_api", availability) == []


# ====================================================================== 2.3 System prompts, technique, guardrails
from atlas.extraction import ExtractionFailed, application_tool, extract, validation_feedback  # noqa: E402
from atlas.prompting import TECHNIQUE, compose, lint_system_prompt  # noqa: E402
from atlas.rules import PolicyGap, check_application, compute_dscr, rules_for  # noqa: E402
from atlas.schemas import ExtractedApplication, LoanApplication  # noqa: E402


def test_2_3_technique_matches_the_task():
    assert TECHNIQUE == {"risk_tier_triage": "zero_shot", "intake": "few_shot", "policy_check": "chain_of_thought"}


def test_2_3_lint_catches_a_demo_prompt():
    demo = "You are a helpful assistant. Process APP-004 for customer B-1004 submitted 2026-10-02."
    assert lint_system_prompt(demo) == ["per-request content: application id", "per-request content: customer id",
                                        "per-request content: specific date", "no edge-case handling"]


@pytest.mark.parametrize("name", ["intake_v1", "intake_v2", "explainer", "memo", "specialist", "judge"])
def test_2_3_every_production_prompt_passes_the_lint(name):
    assert lint_system_prompt(llm.load_prompt(name)) == []


GOOD = dict(application_id="APP-004", business_name="Okafor Mechanical Inc.", customer_id="B-1004",
            loan_type="equipment", jurisdiction="US-NY", amount_requested=180000, term_months=60,
            annual_revenue=1300000, ebitda=240000, existing_annual_debt_service=66000, collateral_value=215000,
            years_in_business=7, purpose="New CNC machine", submitted_on="2026-10-02")


BAD_VALUES = [("amount_requested", "180k"), ("amount_requested", 0), ("amount_requested", 25_000_000),
              ("term_months", 3), ("term_months", 600), ("ebitda", -1), ("years_in_business", 250),
              ("customer_id", "1004"), ("application_id", "APP-4"), ("loan_type", "mortgage"),
              ("jurisdiction", "US-FL")]


def test_2_3_schema_is_enforcement_not_a_request():
    assert LoanApplication(**GOOD).amount_requested == 180000
    accepted = []
    for field, bad in BAD_VALUES:
        try:
            LoanApplication(**{**GOOD, field: bad})
            accepted.append(f"{field}={bad!r}")
        except ValidationError:
            pass
    assert not accepted, f"the schema accepted impossible values: {accepted}"


def test_2_3_schema_guides_the_model_and_minimises_data():
    schema = application_tool()["input_schema"]
    props = schema["properties"]
    assert application_tool()["name"] == "record_application"
    assert "confidence" in props
    assert "annual" in props["ebitda"]["description"].lower(), "the description is part of the prompt"
    assert "term" in props["term_months"]["description"].lower()
    assert not {"ssn", "date_of_birth", "home_address", "guarantor_ssn"} & set(props), "never collect what you don't need"


def test_2_3_validation_feedback_is_specific():
    with pytest.raises(ValidationError) as exc:
        ExtractedApplication(**{**GOOD, "amount_requested": "180k", "confidence": {}})
    text = validation_feedback(exc.value)
    assert "amount_requested" in text and "'180k'" in text
    assert text.splitlines()[-1].startswith("Fix only these fields")


def test_2_3_extraction_forces_the_tool_and_retries_with_feedback():
    result = extract(data_access.load_application_text("APP-004"))
    assert result.application.amount_requested == 180000
    assert result.attempts == 2 and len(result.errors) == 1, "first attempt sends '180k'; your feedback fixes it"
    calls = fake_client().calls
    assert calls[0]["tool_choice"] == {"type": "tool", "name": "record_application"}
    assert "amount_requested" in calls[1]["all_text"] and "180k" in calls[1]["all_text"], \
        "the retry must carry the specific error back to the model"
    assert calls[0]["model"] == config.MODELS["haiku"], "intake runs on its own tier"


def test_2_3_extraction_stops_and_hands_over_instead_of_guessing():
    with pytest.raises(ExtractionFailed) as exc:
        extract(data_access.load_application_text("APP-004"), max_attempts=1)
    assert exc.value.errors


def test_2_3_extraction_keeps_confidence_separate():
    result = extract(data_access.load_application_text("APP-010"))
    assert result.confidence["purpose"] < 0.8 and result.confidence["years_in_business"] < 0.8
    assert not hasattr(result.application, "confidence")


def test_2_3_few_shot_fixes_the_small_model_on_messy_forms():
    v1 = extract(data_access.load_application_text("APP-004"), prompt_name="intake_v1").application
    assert v1.term_months == 36, "zero-shot, the small model confuses the lease term with the loan term"
    llm.reset_client()
    v2 = extract(data_access.load_application_text("APP-004"), prompt_name="intake_v2").application
    expected = gold("APP-004")["expected_fields"]
    assert (v2.term_months, v2.existing_annual_debt_service, v2.years_in_business) == \
           (expected["term_months"], expected["existing_annual_debt_service"], expected["years_in_business"]), \
        "intake_v2.md needs at least two worked <example> blocks covering the hard boundary cases"
    llm.reset_client()
    v2_010 = extract(data_access.load_application_text("APP-010"), prompt_name="intake_v2").application
    assert v2_010.annual_revenue == gold("APP-010")["expected_fields"]["annual_revenue"], "monthly/quarterly -> annual"


# --- guidance is not enforcement: lending rules live in code

def test_2_3_compute_dscr():
    app = app_from_gold("APP-006")
    dscr, total = compute_dscr(app, rules_for("equipment", "US-CA", app.submitted_on))
    assert dscr == pytest.approx(1.132, abs=0.001)
    assert total == pytest.approx(167_860, rel=0.001)


@pytest.mark.parametrize("app_id", [f"APP-{n:03d}" for n in range(1, 11)])
def test_2_3_rules_engine_routes_every_golden_case(app_id):
    app = app_from_gold(app_id)
    score = data_access.get_business_credit_report(app.customer_id)["score"]
    report = check_application(app, score)
    assert report.route == gold(app_id)["expected_route"]
    assert [r.rule_id for r in report.results] == ["credit_score", "dscr", "loan_amount", "ltv", "time_in_business"]
    assert all(r.policy_ref.startswith(report.rules_version + "-") for r in report.results), "every result cites its section"


def test_2_3_borderline_and_jurisdiction_override():
    a6 = check_application(app_from_gold("APP-006"), data_access.get_business_credit_report("B-1006")["score"])
    assert a6.result("dscr").status == "borderline" and a6.route == "investigate"
    assert a6.result("dscr").policy_ref == "POL-EQUIP-v3-1.2"
    a3 = check_application(app_from_gold("APP-003"), data_access.get_business_credit_report("B-1003")["score"])
    ltv = a3.result("ltv")
    assert ltv.threshold == 0.70 and ltv.policy_ref == "POL-CRE-v3-2.2", "New York CRE caps LTV at 0.70 (section 2.2)"
    # the rule set in force depends on product, place AND date (given: rules_for)
    assert rules_for("ag_equipment", "US-TX", date(2026, 10, 15)).version == 3
    v4 = rules_for("ag_equipment", "US-TX", date(2026, 11, 3))
    assert v4.version == 4 and v4.min_dscr == 1.35
    assert rules_for("cre", "US-CA", date(2025, 6, 1)).version == 2
    with pytest.raises(PolicyGap):
        rules_for("ag_equipment", "US-CA", date(2026, 10, 1))


# ====================================================================== 2.4 Context, caching and reuse


def test_2_4_build_system_puts_the_stable_part_first_with_a_breakpoint():
    blocks = llm.build_system("STABLE", "per request")
    assert blocks[0] == {"type": "text", "text": "STABLE", "cache_control": {"type": "ephemeral"}}
    assert blocks[1] == {"type": "text", "text": "per request"}
    assert len(llm.build_system("STABLE")) == 1


def test_2_4_estimate_cost_counts_cache_writes_and_reads():
    haiku = config.MODELS["haiku"]
    million = usage(1_000_000, 1_000_000, 1_000_000, 1_000_000)
    assert llm.estimate_cost(haiku, million) == pytest.approx(0.10 + 0.50 + 0.10 * 1.25 + 0.10 * 0.10)
    sdk_style = usage(1000, 100, None, None)
    assert llm.estimate_cost(haiku, sdk_style) == pytest.approx((1000 * 0.10 + 100 * 0.50) / 1e6)


def test_2_4_stable_prefix_is_written_once_then_read():
    stable = llm.load_prompt("explainer")
    with start_trace("cache") as trace:
        for i in range(3):
            llm.call("policy_check", [{"role": "user", "content": f"request {i}"}],
                     system=llm.build_system(stable, f"Request id: req-{i}"))
    assert [s.attrs["cache"] for s in trace.llm_calls()] == ["write", "hit", "hit"]
    assert trace.llm_calls()[2].attrs["cost_usd"] < trace.llm_calls()[0].attrs["cost_usd"]


def test_2_4_a_request_id_in_front_breaks_the_prefix_silently():
    stable = llm.load_prompt("explainer")
    with start_trace("broken") as trace:
        for i in range(3):
            llm.call("policy_check", [{"role": "user", "content": f"request {i}"}],
                     system=llm.build_system(f"Request id: req-{i}\n" + stable))
    assert [s.attrs["cache"] for s in trace.llm_calls()] == ["write", "write", "write"], \
        "no error, no hit: the fix is reordering, not shrinking the document"


def test_2_4_compose_resolves_modules_recursively():
    modules = {"a": "A({{include: b}})", "b": "B", "x": "{{include: y}}", "y": "{{include: x}}"}
    assert compose("start {{include: a}} end", modules.__getitem__) == "start A(B) end"
    assert compose("no includes", modules.__getitem__) == "no includes"
    with pytest.raises(ValueError):
        compose("{{include: x}}", modules.__getitem__)


def test_2_4_shared_modules_are_written_once_and_used_everywhere():
    shared = (config.PROMPTS / "shared" / "untrusted_data.md").read_text().strip()
    for name in ("intake_v2", "explainer", "memo", "specialist"):
        text = llm.load_prompt(name)
        assert "{{include" not in text
        assert shared in text, f"{name} should include shared/untrusted_data"
