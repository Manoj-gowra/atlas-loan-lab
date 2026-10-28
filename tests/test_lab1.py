"""LAB 1 - Solution design and architecture (course Chapter 1) + "What This Exam Tests".

    pytest tests/test_lab1.py            # your code
    pytest tests/test_lab1.py --solution # the reference
Guide: docs/LAB1.md. Every section below is one course lesson.
"""
import json

import pytest

# ====================================================================== 0. What This Exam Tests
from atlas.controls import best_risk_reduction, classify_control


@pytest.mark.parametrize("option, expected", [
    ("Remove the refund and delete tools from the agent", "preventive"),
    ("Revoke the shared admin credential and scope one per component", "preventive"),
    ("Log every use of the refund tool and review the log weekly", "detective"),
    ("Add a confirmation prompt before each refund", "compensating"),
    ("Switch to a bigger model that follows instructions better", "not_a_control"),
    ("Rewrite the onboarding wiki", "unknown"),
])
def test_0_classify_control_names_the_exam_distractors(option, expected):
    assert classify_control(option) == expected


def test_0_bigger_model_is_never_a_control_even_if_it_mentions_scope():
    # "not a control" is checked FIRST: a bigger model confuses instruction-following with authorization
    assert classify_control("Use a more capable model to restrict itself to read-only tickets") == "not_a_control"


def test_0_best_risk_reduction_is_the_preventive_option():
    options = ["Log every refund to the SIEM", "Add a confirmation step before refunds",
               "Use a larger model", "Remove the refund and delete tools; the agent only reads tickets"]
    assert best_risk_reduction(options) == options[3]
    with pytest.raises(ValueError):
        best_risk_reduction(options[:3])


# ====================================================================== 1.1 Business problem -> architecture
from atlas import design  # noqa: E402


def test_1_1_decomposition_has_the_four_tasks():
    names = [t.name for t in design.DECOMPOSITION]
    assert names == ["intake", "policy_check", "drafting", "decision"], "four tasks hidden in the mandate"


def test_1_1_decomposition_keeps_the_decision_human():
    tasks = {t.name: t for t in design.DECOMPOSITION}
    decision = tasks["decision"]
    assert decision.risk == "high" and decision.reversible is False and decision.disposition == "human"
    assert tasks["intake"].disposition == "automate" and tasks["intake"].moves_metric == "yes"
    assert tasks["policy_check"].disposition == "automate"
    assert tasks["drafting"].disposition == "assist", "a draft the officer edits is assistive"
    for t in design.DECOMPOSITION:
        assert t.input and t.output, f"{t.name}: name the input and the output"
        if t.disposition == "automate":
            assert t.reversible and t.risk != "high", "automate only what is reversible and not high risk"


def test_1_1_value_numbers_from_discovery():
    hours = design.officer_hours_saved(90, 4000, 2 / 3)
    assert hours == pytest.approx(4000)
    ceiling = design.max_cost_per_application(hours, 85, 4000)
    assert ceiling == pytest.approx(85.0), "value created per application = the cost ceiling"


def test_1_1_slos_are_measurable_targets_from_the_notes():
    s = design.SLOS
    assert (s.p95_case_ready_s, s.max_avg_cost_usd, s.min_field_accuracy, s.min_route_accuracy, s.max_review_rate) == \
           pytest.approx((60, 0.05, 0.95, 0.90, 0.30))


# ====================================================================== 1.2 Architecture patterns
from atlas.design import Pattern, choose_pattern  # noqa: E402


def test_1_2_decision_framework_stops_at_the_first_yes():
    assert choose_pattern(single_bounded_call=True, flowchart_known=True) is Pattern.AUGMENTED_LLM
    assert choose_pattern(single_bounded_call=False, flowchart_known=True) is Pattern.WORKFLOW
    assert choose_pattern(single_bounded_call=False, flowchart_known=False) is Pattern.AGENT


def test_1_2_task_design_uses_the_least_autonomy_each_task_needs():
    td = design.TASK_DESIGN
    assert td["intake"].pattern is Pattern.AUGMENTED_LLM
    assert td["policy_check"].pattern is Pattern.WORKFLOW, "routing among known options is still a workflow"
    assert td["drafting"].pattern is Pattern.WORKFLOW
    assert td["investigation"].pattern is Pattern.AGENT
    assert td["decision"].pattern is Pattern.HUMAN and td["decision"].model is None
    agents = [name for name, d in td.items() if d.pattern is Pattern.AGENT]
    assert agents == ["investigation"], "only the borderline investigation needs an agent"


def test_1_2_every_choice_has_a_reason_and_its_own_tier():
    td = design.TASK_DESIGN
    for name in ("intake", "policy_check", "drafting", "investigation", "decision"):
        assert len(td[name].why.split()) >= 6, f"{name}: write the one-sentence reason you'd say in an interview"
    assert td["intake"].model == "haiku", "bounded, high volume: compact tier"
    assert td["investigation"].model == "opus", "low volume, high consequence: most capable tier"
    assert len({d.model for d in td.values() if d.model}) >= 2, "one tier for every component is the design error"


# ====================================================================== 1.3 Multi-agent systems
from atlas.coordination import (BRIEF_FIELDS, SpecialistReport, specialist_brief,  # noqa: E402
                                synthesize)


@pytest.mark.parametrize("independent, tools, polluted, expected", [
    (True, 3, False, True), (False, 18, False, True), (False, 4, True, True), (False, 5, False, False)])
def test_1_3_three_signals_justify_a_coordinator(independent, tools, polluted, expected):
    assert design.needs_coordinator(independent, tools, polluted) is expected


FACTS = {"application_id": "APP-006", "customer_id": "B-1006", "business name": "Herrera Electrical Inc.",
         "loan type": "equipment", "jurisdiction": "US-CA", "amount requested": 320000.0,
         "flagged rules": "dscr borderline (DSCR 1.13 vs minimum 1.20)", "stated EBITDA": 190000.0,
         "total annual debt service": 167800.0, "minimum DSCR": 1.2, "DSCR": 1.132, "LTV": 0.842,
         "maximum LTV": 0.85, "years in business": 8.0, "annual revenue": 1900000.0, "purpose": "Bucket truck"}


def test_1_3_briefs_are_scoped_not_the_whole_case():
    for role in ("financial_ratio", "business_history", "industry_risk"):
        brief = specialist_brief(role, FACTS)
        assert "APP-006" in brief and "B-1006" in brief
        assert "purpose" not in brief and "annual revenue" not in brief, f"{role}: don't hand over the whole case"
    assert len(BRIEF_FIELDS["industry_risk"]) < len(FACTS)


def test_1_3_financial_ratio_brief_has_what_it_needs_to_recompute_dscr():
    brief = specialist_brief("financial_ratio", FACTS)
    for key in ("stated EBITDA", "total annual debt service", "minimum DSCR"):
        assert f"{key}:" in brief, f"financial_ratio cannot recompute DSCR without '{key}'"
    assert "stated EBITDA" not in specialist_brief("industry_risk", FACTS)
    assert "loan type: equipment" in specialist_brief("industry_risk", FACTS)


def test_1_3_brief_keeps_brief_fields_order():
    brief = specialist_brief("financial_ratio", FACTS)
    keys = [line.split(":")[0] for line in brief.splitlines()[2:-1]]
    assert keys == [k for k in BRIEF_FIELDS["financial_ratio"] if k in FACTS]


def _report(role, recommendation="support_approval", status="completed", findings=None, metrics=None):
    return SpecialistReport(role, status, findings or [], recommendation, metrics=metrics or {})


def test_1_3_synthesis_attributes_every_finding_to_the_session_that_produced_it():
    fr = _report("financial_ratio", findings=[
        {"finding": "verified EBITDA 236k", "in_scope": True, "confidence": "high", "source_specialist": "coordinator"},
        {"finding": "possible affiliate", "in_scope": False, "confidence": "low"}],
        metrics={"verified_ebitda": 236000})
    bh = _report("business_history", findings=[
        {"finding": "affiliate not reviewed", "in_scope": True, "confidence": "medium",
         "unable_to_check": "affiliate B-1012 is outside scope"}])
    result = synthesize([fr, bh, _report("industry_risk", "inconclusive")])
    assert [f.source_specialist for f in result.findings] == ["financial_ratio", "business_history"], \
        "provenance comes from the code that ran the specialist, not from what the text claims"
    assert [f.finding for f in result.unverified_asides] == ["possible affiliate"], "label out-of-scope asides"
    assert result.unable_to_check == ["business_history: affiliate B-1012 is outside scope"]
    assert result.metrics["financial_ratio"] == {"verified_ebitda": 236000}
    assert result.specialists == {"financial_ratio": "completed", "business_history": "completed",
                                  "industry_risk": "completed"}
    assert result.recommendations["industry_risk"] == "inconclusive"
    assert result.status == "completed" and result.recommendation == "approve_with_conditions"


def test_1_3_synthesis_recommendation_rules():
    assert synthesize([_report("a"), _report("b", "support_decline")]).recommendation == "decline"
    assert synthesize([_report("a", "inconclusive"), _report("b", "inconclusive")]).recommendation == "refer_to_human"
    esc = synthesize([_report("a"), _report("b", status="escalated")])
    assert esc.status == "escalated" and esc.recommendation == "refer_to_human" and "b" in esc.reason
    assert synthesize([_report("a"), _report("b", "support_decline")]).specialists_disagree


# ====================================================================== 1.4 Reference architectures + feedback
from atlas.design import REFERENCE_ARCHITECTURES, reference_architecture  # noqa: E402
from atlas.feedback import FeedbackStore  # noqa: E402


@pytest.mark.parametrize("signals, expected", [
    ({"single_transformation": True}, "augmented_llm"),
    ({"answers_from_reference_docs": True}, "rag_assistant"),
    ({"fixed_steps": True}, "fixed_workflow"),
    ({"path_unknown": True}, "agentic_investigator"),
    ({"parallel_specialists": True, "path_unknown": True}, "coordinator_specialists"),
    ({"checkpoint_before_action": True, "fixed_steps": True}, "hitl_review_gate"),
])
def test_1_4_six_reference_architectures(signals, expected):
    assert reference_architecture(**signals) == expected
    assert expected in REFERENCE_ARCHITECTURES


def test_1_4_reference_architecture_needs_a_signal():
    with pytest.raises(ValueError):
        reference_architecture()


def test_1_4_feedback_record_keeps_the_pair_and_its_context(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.jsonl")
    item = store.record("APP-004", "intake", "extraction", "term_months", 36, 60, "officer-17")
    assert item["original"] == 36 and item["corrected"] == 60
    assert {"app_id", "component", "step", "field", "officer_id", "ts"} <= set(item)
    line = json.loads((tmp_path / "feedback.jsonl").read_text().splitlines()[0])
    assert line["field"] == "term_months" and line["component"] == "intake"


def test_1_4_logging_is_not_a_feedback_loop(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.jsonl")
    with pytest.raises(ValueError):
        store.record("APP-004", "intake", "extraction", "term_months", None, 60, "officer-17")
    with pytest.raises(ValueError):
        store.record("APP-004", "intake", "extraction", "term_months", 36, None, "officer-17")
    assert store.all() == []
