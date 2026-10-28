"""LAB 4 - Evaluation, testing and optimization (course Chapter 4).

    pytest tests/test_lab4.py [--solution]
Guide: docs/LAB4.md. Needs Labs 1-3 (the whole pipeline runs here).
"""
from datetime import date

import pytest
from _helpers import fake_client, gold, process

from atlas import config, data_access, llm
from atlas.design import SLOS
from atlas.evals import (CaseResult, check_slos, load_golden, run_eval, score_case, summarize,
                         thin_strata, weak_strata)
from atlas.pipeline import CaseFile
from atlas.tracing import Span, Trace


def evaluate(**kwargs):
    llm.reset_client()
    data_access.reset_simulations()
    return summarize(run_eval(**kwargs))


def result(category="clean", loan_type="term", correct=12, total=12, route_ok=True, review=False, cost=0.02,
           latency=10.0, safety=True, security=True):
    return CaseResult("APP-X", category, loan_type, total, correct, [], route_ok, review, True, safety, security,
                      cost, latency)


# ====================================================================== 4.1 Metrics and test frameworks


def test_4_1_score_case_on_all_five_axes():
    r = score_case(process("APP-004"), gold("APP-004"))
    assert (r.fields_total, r.fields_correct, r.wrong_fields) == (12, 12, [])
    assert r.route_ok and r.safety_ok and r.security_ok and r.flags_ok
    assert (r.category, r.loan_type) == ("messy", "equipment")
    assert r.cost_usd > 0 and r.latency_s > 0


def test_4_1_score_case_names_the_wrong_fields():
    r = score_case(process("APP-004", prompt_name="intake_v1"), gold("APP-004"))
    assert r.wrong_fields == ["term_months", "existing_annual_debt_service", "years_in_business"]
    assert r.fields_correct == 9


def test_4_1_safety_and_security_are_separate_axes():
    case = CaseFile("APP-001", trace=Trace("APP-001"))
    case.memo = "Recommendation: APPROVE - the applicant is PRE-APPROVED."
    case.trace.spans.append(Span("tool:get_business_credit_report", "tool",
                                 attrs={"authorized": False, "executed": True}))
    r = score_case(case, gold("APP-001"))
    assert r.safety_ok is False and r.security_ok is False
    assert r.fields_correct == 0 and r.route_ok is False, "no application, no report: nothing is correct"
    flagged = CaseFile("APP-001", trace=Trace("APP-001"), flags=["prohibited_factor:age"])
    assert score_case(flagged, gold("APP-001")).safety_ok is False


def test_4_1_summarize_is_stratified():
    results = [result("clean", "term"), result("clean", "equipment", latency=50.0),
               result("messy", "equipment", correct=6, route_ok=False, review=True, cost=0.05, latency=20.0)]
    s = summarize(results)
    assert set(s) == {"overall", "by_category", "by_loan_type"}
    o = s["overall"]
    assert o["n"] == 3 and o["field_accuracy"] == pytest.approx(30 / 36, abs=1e-4)
    assert o["route_accuracy"] == pytest.approx(0.6667, abs=1e-4) and o["review_rate"] == pytest.approx(0.3333, abs=1e-4)
    assert o["avg_cost_usd"] == pytest.approx(0.03) and o["p95_latency_s"] == 50.0, "latency is a distribution: the tail"
    assert s["by_category"]["messy"]["field_accuracy"] == 0.5 and s["by_category"]["clean"]["field_accuracy"] == 1.0
    assert s["by_loan_type"]["equipment"]["n"] == 2
    assert {"safety_rate", "security_rate", "flags_ok_rate"} <= set(o)


def test_4_1_slos_and_weak_strata():
    good_overall = summarize([result()] * 19 + [result("messy", "equipment", correct=6)])
    checks = check_slos(good_overall, SLOS)
    assert set(checks) == {"p95_case_ready_s", "max_avg_cost_usd", "min_field_accuracy", "min_route_accuracy",
                           "max_review_rate"}
    assert all(checks.values()), "the aggregate passes..."
    assert weak_strata(good_overall, SLOS) == ["category:messy", "loan_type:equipment"], "...the strata do not"
    slow = summarize([result(latency=90.0)])
    assert check_slos(slow, SLOS)["p95_case_ready_s"] is False


def test_4_1_thin_strata_in_the_golden_set():
    golden = load_golden()
    assert thin_strata(golden, "category", 2) == {"clear_decline": 1, "injection": 1}
    assert thin_strata(golden, "loan_type", 1) == {}


def test_4_1_the_current_system_meets_every_slo():
    s = evaluate()
    assert set(s["by_category"]) == {"clean", "messy", "clear_decline", "borderline", "injection"}
    assert all(check_slos(s, SLOS).values()), check_slos(s, SLOS)
    assert weak_strata(s, SLOS) == []
    assert s["overall"]["field_accuracy"] == 1.0 and s["overall"]["security_rate"] == 1.0


# --- LLM-as-judge, calibrated by human review
from atlas.judge import CRITERIA, agreement, judge_explanation, load_labels  # noqa: E402


def test_4_1_judge_rubric_is_observable():
    ids = [c for c, _ in CRITERIA]
    assert {"names_flagged_rules", "cites_flagged_sections", "no_decision_language"} <= set(ids)
    assert all(len(desc.split()) >= 5 for _, desc in CRITERIA), "describe what to OBSERVE, not 'rate quality'"


def test_4_1_judge_forces_a_structured_verdict():
    case = process("APP-006")
    verdict = judge_explanation(case.rule_report, case.explanation.text)
    assert set(verdict["criteria"]) == {c for c, _ in CRITERIA} and verdict["passed"] is True
    judge_call = fake_client().calls[-1]
    assert judge_call["tool_choice"] == {"type": "tool", "name": "record_judgment"}
    assert judge_call["model"] == config.MODELS["sonnet"]
    assert '<criterion id="names_flagged_rules">' in judge_call["system_text"], "rubric in the stable system prompt"
    bad = judge_explanation(case.rule_report, "Looks fine. I recommend approval.")
    assert bad["passed"] is False and bad["criteria"]["no_decision_language"] is False


def test_4_1_agreement():
    labels = [{"app_id": "A", "human_pass": True}, {"app_id": "B", "human_pass": False}, {"app_id": "C", "human_pass": True}]
    assert agreement({"A": True, "B": True}, labels) == 0.5
    assert agreement({"A": True, "B": False, "C": True, "Z": False}, labels) == 1.0
    assert agreement({}, labels) == 0.0


def test_4_1_human_labels_calibrate_the_judge():
    labels = load_labels()
    cases = {row["app_id"]: process(row["app_id"]) for row in labels}
    first_draft = [c for c in CRITERIA if c[0] != "gives_next_step"]
    before = {a: judge_explanation(c.rule_report, c.explanation.text, first_draft)["passed"] for a, c in cases.items()}
    after = {a: judge_explanation(c.rule_report, c.explanation.text)["passed"] for a, c in cases.items()}
    assert agreement(before, labels) == 0.8, "the humans failed APP-009 for a reason the first rubric ignores"
    assert "gives_next_step" in {c for c, _ in CRITERIA}, "add the criterion the human labels revealed"
    assert agreement(after, labels) == 1.0


# ====================================================================== 4.2 A/B testing and iterative improvement
from atlas.experiments import assert_single_variable, differing_variables, run_ab, undersized_strata  # noqa: E402
from atlas.feedback import FeedbackStore  # noqa: E402


def test_4_2_isolate_one_variable():
    a = {"prompt_name": "intake_v2", "intake_model": "claude-haiku-5-5"}
    assert differing_variables(a, {**a, "prompt_name": "intake_v1"}) == ["prompt_name"]
    assert differing_variables(a, {"prompt_name": "intake_v2"}) == ["intake_model"]
    assert assert_single_variable(a, {**a, "intake_model": "claude-sonnet-5-5"}) == "intake_model"
    with pytest.raises(ValueError):
        assert_single_variable(a, {"prompt_name": "intake_v1", "intake_model": "claude-sonnet-5-5"})
    with pytest.raises(ValueError):
        assert_single_variable(a, dict(a))


def test_4_2_enough_data_per_stratum():
    assert undersized_strata({"clean": 400, "messy": 12, "injection": 3}) == ["injection", "messy"]
    assert undersized_strata({"clean": 400}, minimum=30) == []


def test_4_2_ab_prompt_fix_on_the_same_dataset():
    small = config.MODELS["haiku"]
    ab = run_ab({"prompt_name": "intake_v2", "intake_model": small},
                {"prompt_name": "intake_v1", "intake_model": small}, evaluate)
    assert ab["variable"] == "prompt_name"
    a, b = ab["a"], ab["b"]
    assert a["by_category"]["messy"]["field_accuracy"] == 1.0
    assert b["by_category"]["messy"]["field_accuracy"] < 0.85, "zero-shot fails the messy forms"
    assert b["overall"]["field_accuracy"] >= SLOS.min_field_accuracy, "...while the aggregate still looks fine"
    assert "category:messy" in weak_strata(b, SLOS)


def test_4_2_prompt_fix_vs_model_upgrade():
    ab = run_ab({"prompt_name": "intake_v1", "intake_model": config.MODELS["haiku"]},
                {"prompt_name": "intake_v1", "intake_model": config.MODELS["sonnet"]}, evaluate)
    assert ab["variable"] == "intake_model"
    assert ab["b"]["by_category"]["messy"]["field_accuracy"] == 1.0
    assert ab["b"]["overall"]["avg_cost_usd"] > ab["a"]["overall"]["avg_cost_usd"], "the upgrade costs more per case"


def test_4_2_officer_corrections_become_regression_cases():
    store = FeedbackStore()
    store.record("APP-004", "intake", "extraction", "term_months", 36, 60, "officer-17")
    store.record("APP-004", "intake", "extraction", "years_in_business", 70, 6, "officer-17")
    store.record("APP-004", "intake", "extraction", "years_in_business", 6, 7, "officer-21")
    store.record("APP-010", "intake", "extraction", "ebitda", 62500, 250000, "officer-17")
    rows = store.to_golden_rows()
    assert rows == [
        {"app_id": "APP-004", "category": "officer_correction", "expected_fields": {"term_months": 60, "years_in_business": 7}},
        {"app_id": "APP-010", "category": "officer_correction", "expected_fields": {"ebitda": 250000}},
    ]


# ====================================================================== 4.3 Diagnosing system failures
from atlas.diagnosis import diagnose, semantic_checks, what_changed  # noqa: E402
from atlas.schemas import LoanApplication  # noqa: E402


@pytest.mark.parametrize("present, clear, reliable, cause", [
    (False, True, True, "retrieval_or_grounding"),
    (True, False, True, "prompt_failure"),
    (True, True, True, "model_mismatch"),
    (True, True, False, "needs_more_evidence"),
])
def test_4_3_three_causes_three_fixes(present, clear, reliable, cause):
    assert diagnose(present, clear, reliable) == cause


def test_4_3_structural_pass_is_not_semantic_pass():
    fields = dict(gold("APP-001")["expected_fields"], purpose="x", submitted_on=date(2027, 2, 1),
                  ebitda=3_000_000, existing_annual_debt_service=2_500_000, collateral_value=0)
    app = LoanApplication(**fields)  # the schema is happy...
    assert semantic_checks(app) == ["EBITDA exceeds revenue", "debt service exceeds revenue", "no collateral value",
                                    "submitted in the future"]
    assert semantic_checks(app, today=date(2027, 3, 1))[-1] != "submitted in the future"
    clean = LoanApplication(**dict(gold("APP-001")["expected_fields"], purpose="x", submitted_on=date(2026, 9, 1)))
    assert semantic_checks(clean) == []


def test_4_3_what_changed_right_before():
    log = [{"ts": "2026-10-01T10:00:00+00:00", "what": "prompt intake_v2 deployed"},
           {"ts": "2026-10-20T08:00:00+00:00", "what": "policy documents refreshed"},
           {"ts": "2026-10-21T02:00:00+00:00", "what": "dependency update"},
           {"ts": "2026-10-23T09:00:00+00:00", "what": "after the regression"}]
    assert what_changed(log, "2026-10-22T09:00:00+00:00")["what"] == "dependency update"
    assert what_changed(log, "2026-10-22T09:00:00+00:00", window_hours=12) is None
    assert what_changed([], "2026-10-22T09:00:00+00:00") is None


# ====================================================================== 4.4 Optimizing cost, latency, performance
from atlas.optimize import accept_optimization, find_waste, processing_plan  # noqa: E402


def test_4_4_find_waste_in_the_traces():
    cases = [process(a) for a in ("APP-001", "APP-002", "APP-005", "APP-006")]
    waste = find_waste(cases)
    assert set(waste["cache_miss_rate"]) == {"intake", "policy_check"}
    assert 0 < waste["cache_miss_rate"]["policy_check"] < 1
    cited = sum(len(c.explanation.citations) for c in cases)
    retrieved = sum(len(c.explanation.chunk_ids) for c in cases)
    assert waste["retrieval_utilization"] == round(cited / retrieved, 4)
    assert find_waste([]) == {"cache_miss_rate": {}, "retrieval_utilization": 0.0}


def test_4_4_batch_when_nobody_is_waiting():
    nightly = processing_plan(400, 0.03, someone_waiting=False)
    assert nightly == {"mode": "batch", "total_cost": 6.0, "savings": 6.0}
    live = processing_plan(400, 0.03, someone_waiting=True)
    assert live == {"mode": "synchronous", "total_cost": 12.0, "savings": 0.0}


def test_4_4_optimize_only_after_correctness():
    before = summarize([result()] * 10)
    cheaper_same = summarize([result(cost=0.01)] * 10)
    cheaper_wrong = summarize([result(cost=0.01, correct=11)] * 10)
    assert accept_optimization(before, cheaper_same, SLOS)
    assert not accept_optimization(before, cheaper_wrong, SLOS), "a wrong answer faster and cheaper is not better"
    over_budget = summarize([result(cost=0.2)] * 10)
    assert not accept_optimization(before, over_budget, SLOS)

