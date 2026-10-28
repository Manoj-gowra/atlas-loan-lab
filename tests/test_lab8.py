"""LAB 8 - Capstone: the cross-domain scenario (course Chapter 8).

    pytest tests/test_lab8.py [--solution]
Guide: docs/LAB8.md. Needs Labs 1-7. Case 2 (the stale-index near miss) is reproduced in a sandbox;
case 1 (renewals) is a design you defend.
"""
import re
from types import SimpleNamespace

import pytest

from atlas import config, diagnosis, drill, rag
from atlas.capstone import RENEWALS_DESIGN, citation_conflicts
from atlas.escalation import escalation_triggers
from atlas.pipeline import CaseFile
from atlas.rules import RuleResult


def report_with(*refs):
    results = [RuleResult(rule_id, "pass", 0, 0, ref) for rule_id, ref in refs]
    return SimpleNamespace(results=results, route="approve")


# ====================================================================== case 2: the near-miss regression


def test_8_citation_conflicts_find_a_different_version_of_the_rule_applied():
    report = report_with(("dscr", "POL-AGEQ-v4-1.2"), ("ltv", "POL-AGEQ-v4-1.4"))
    stale = SimpleNamespace(citations=["POL-AGEQ-v3-1.2", "POL-AGEQ-v4-1.4", "POL-GEN-v1-1.1", "POL-AGEQ-v3-2.1"])
    assert citation_conflicts(report, stale) == [{"rule_id": "dscr", "applied": "POL-AGEQ-v4-1.2", "cited": "POL-AGEQ-v3-1.2"}]
    fresh = SimpleNamespace(citations=["POL-AGEQ-v4-1.2", "POL-AGEQ-v4-1.4"])
    assert citation_conflicts(report, fresh) == []
    other_product = SimpleNamespace(citations=["POL-EQUIP-v3-1.2"])
    assert citation_conflicts(report, other_product) == [], "same section number, different policy: no conflict"


def test_8_a_stale_citation_escalates_by_design():
    case = CaseFile("APP-101")
    case.rule_report = report_with(("dscr", "POL-AGEQ-v4-1.2"))
    case.explanation = SimpleNamespace(citations=["POL-AGEQ-v3-1.2"], text="", flagged=False)
    assert "conflicting_evidence" in escalation_triggers(case), \
        "a citation out of step with the policy applied must not depend on an officer's diligence"


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """The drill's timeline, inside this test's own runs/ folder."""
    monkeypatch.setenv("ATLAS_POLICY_DIR", str(config.RUNS / "policies"))
    drill.setup_before_update()
    drill.publish_v4()
    return config.RUNS


def test_8_reproduce_detect_diagnose_fix_verify(sandbox):
    # 1. reproduce: v4 is published, the index is not rebuilt
    index = rag.get_index()
    assert index.is_stale(config.policy_dir()), "the index no longer matches its sources"
    before = drill.run_cases(["APP-001", "APP-006"] + drill.DRILL_APPS)
    for app_id in drill.DRILL_APPS:
        case = before[app_id]
        assert case.rule_report.rules_version == "POL-AGEQ-v4", "the rules engine applies v4..."
        assert citation_conflicts(case.rule_report, case.explanation), "...while the explanation cites v3"
        assert "conflicting_evidence" in case.triggers
    # 2. detect: only the stratified view shows it
    card = drill.scorecard(before)
    assert card["ag_equipment"]["citation_conflict_rate"] == 1.0
    assert card["term"]["citation_conflict_rate"] == 0.0 and card["equipment"]["citation_conflict_rate"] == 0.0
    assert card["ag_equipment"]["judge_pass_rate"] < card["term"]["judge_pass_rate"]
    # 3. diagnose: what changed right before the regression started?
    culprit = diagnosis.what_changed(drill.change_log(), drill.REGRESSION_START, window_hours=168)
    assert culprit["ts"].startswith("2026-10-29") and "SKIPPED" in culprit["what"]
    # 4. fix, then re-run the SAME stratified check
    rag.refresh_index("post-incident rebuild")
    assert not rag.get_index().is_stale(config.policy_dir())
    after = drill.run_cases(["APP-001", "APP-006"] + drill.DRILL_APPS)
    card_after = drill.scorecard(after)
    assert card_after["ag_equipment"]["citation_conflict_rate"] == 0.0
    assert card_after["ag_equipment"]["judge_pass_rate"] > card["ag_equipment"]["judge_pass_rate"]
    assert card_after["term"] == card["term"], "nothing else regressed"
    assert not any(citation_conflicts(after[a].rule_report, after[a].explanation) for a in drill.DRILL_APPS)


def test_8_the_incident_note_is_honest_and_complete():
    path = config.WORKSPACE / "docs" / "incident_note.md"
    assert path.exists(), "write docs/incident_note.md after running scripts/incident_drill.py"
    text = path.read_text()
    assert "TODO" not in text
    parts = re.split(r"(?m)^## +(.+)$", text)
    body = {parts[i].strip().lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    for heading in ("what happened", "why the dashboard missed it", "root cause", "fix and verification",
                    "what we tell stakeholders"):
        assert any(k.startswith(heading) and v for k, v in body.items()), f"section '{heading}' is empty or missing"
    design_section = next(v for k, v in body.items() if k.startswith("what changes so design catches it"))
    assert "citation_conflicts" in design_section or "conflicting_evidence" in design_section
    root = next(v for k, v in body.items() if k.startswith("root cause")).lower()
    assert "stale" in root and "2026-10-29" in root, "name the cause and the event you found in the change log"
    assert "minor hiccup" not in text.lower()


# ====================================================================== case 1: the renewals request


def test_8_renewals_design_tests_the_pattern_instead_of_copying_it():
    d = RENEWALS_DESIGN
    assert "TODO" not in str(d)
    need = d["need"].lower()
    assert "time" in need and ("quarter" in need or "routine" in need), "the pain is time at quarter-end, not errors"
    assert d["pattern_routine"] == "workflow" and d["pattern_flagged"] == "agent"
    signals = " ".join(d["flag_signals"]).lower()
    assert len(d["flag_signals"]) >= 3 and "covenant" in signals and "revenue" in signals and "missing" in signals
    assert (d["model_routine"], d["model_flagged"]) == ("haiku", "opus")


def test_8_renewals_supporting_pieces_do_not_transfer_by_default():
    d = RENEWALS_DESIGN
    assert d["reuse_origination_index"] is False, "legacy renewal policy versions: build a fresh index"
    assert d["reuse_origination_eval_set"] is False and set(d["eval_strata"]) >= {"standard", "flagged"}
    assert d["reuse_escalation_definitions"] is False, "same four triggers, renewal-specific definitions"
    assert len(d["tell_the_vp"].split()) >= 8, "say honestly what you will deliver instead of a copy"
