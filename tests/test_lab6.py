"""LAB 6 - Stakeholder communication and the solution life cycle (course Chapter 6).

    pytest tests/test_lab6.py [--solution]
Guide: docs/LAB6.md. Code in atlas/requirements.py and atlas/communication.py; documents in docs/
(the tests read YOUR docs/ folder, or solutions/docs with --solution).
"""
import re

import pytest

from atlas import config, design, escalation, monitoring
from atlas.communication import JARGON, is_measurable, lint_decision, route_feedback, summarize_for
from atlas.requirements import CONSTRAINTS, NEED_STATEMENT, REQUIREMENTS, classify_constraint

DOCS = config.WORKSPACE / "docs"


def read_doc(name: str) -> str:
    path = DOCS / name
    assert path.exists(), f"missing {path}"
    text = path.read_text()
    assert "TODO" not in text, f"{name} still has TODOs"
    return text


def sections(text: str) -> dict[str, str]:
    """'## Heading' -> body text."""
    parts = re.split(r"(?m)^## +(.+)$", text)
    return {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


# ====================================================================== 6.1 Structured discovery


@pytest.mark.parametrize("answer, kind", [
    ("Then we'd have to revisit the whole approach - replacing the LOS is a multi-year programme.", "binding"),
    ("We cannot do it. That is how we passed the regulator's cloud review.", "binding"),
    ("I'd prefer it, but officers would be fine with an equivalent view.", "preference"),
    ("Nice to have; we could work around it.", "preference"),
    ("Let me think about it.", "unclear"),
])
def test_6_1_the_binding_test(answer, kind):
    assert classify_constraint(answer) == kind


def test_6_1_the_need_not_the_want():
    need = NEED_STATEMENT.lower()
    assert "todo" not in need and "officer" in need
    assert "standard" in need or "routine" in need, "the need is officer time on the routine majority"
    assert "reads loan documents" not in need, "that is the stated WANT, in solution language"


def test_6_1_requirements_are_checkable():
    assert len(REQUIREMENTS) >= 6
    for r in REQUIREMENTS:
        assert r.metric and re.search(r"\d", r.target), f"{r.id}: how would you check it once built?"
    targets = " ".join(r.target for r in REQUIREMENTS)
    for slo in ("60", "0.95", "0.90", "0.30", "0.05"):
        assert slo in targets, f"no requirement carries the {slo} target from discovery"


def test_6_1_constraints_are_tested_not_assumed():
    by_text = {c.text.lower(): c for c in CONSTRAINTS}
    assert len(CONSTRAINTS) >= 5
    los = next(c for t, c in by_text.items() if "origination" in t)
    dashboard = next(c for t, c in by_text.items() if "dashboard" in t)
    assert los.binding and not dashboard.binding
    for c in CONSTRAINTS:
        assert classify_constraint(c.reason) == ("binding" if c.binding else "preference"), \
            f"{c.id}: the recorded reason must justify the classification"


# ====================================================================== 6.2 Communicating decisions


@pytest.mark.parametrize("statement, ok", [
    ("95% of case files are ready within 60 seconds", True),
    ("Average model cost at most $0.05 per application", True),
    ("Fast and reliable case files", False),
    ("Accurate enough for 1 team", False),
])
def test_6_2_an_sla_is_measurable(statement, ok):
    assert is_measurable(statement) is ok


def test_6_2_decision_records_name_the_trade_off():
    assert lint_decision({"decision": "x", "why": "y", "gives_up": "z", "alternatives": "w"}) == []
    assert lint_decision({"decision": "Use opus", "why": "judgment"}) == ["missing gives_up", "missing alternatives"]


def test_6_2_route_feedback_honestly():
    assert route_feedback(True, True) == "change_the_design"
    assert route_feedback(False, True) == "explain_the_constraint", "not a quiet concession to the loudest voice"
    assert route_feedback(False, False) == "acknowledge_and_explain_the_trade_off"


SUMMARY = {"overall": {"n": 10, "field_accuracy": 0.9583, "route_accuracy": 0.9, "review_rate": 0.1,
                       "avg_cost_usd": 0.0251, "p95_latency_s": 18.07}}


def test_6_2_same_status_two_audiences():
    exec_text = summarize_for("executive", SUMMARY, design.SLOS, ["category:messy"])
    lowered = exec_text.lower()
    assert not [j for j in JARGON if re.search(rf"\b{j}\b", lowered)], "translate, don't paste the dashboard"
    assert len(exec_text.splitlines()) == 6 and "MISSED" not in exec_text and "messy" in exec_text
    assert "18 seconds" in exec_text and "$0.025" in exec_text
    tech = summarize_for("technical", SUMMARY, design.SLOS, ["category:messy"])
    for name in ("p95_latency_s", "avg_cost_usd", "field_accuracy", "route_accuracy", "review_rate", "category:messy"):
        assert name in tech
    worse = {"overall": {**SUMMARY["overall"], "field_accuracy": 0.8}}
    assert "MISSED" in summarize_for("executive", worse, design.SLOS, [])
    with pytest.raises(ValueError):
        summarize_for("board", SUMMARY, design.SLOS, [])


def test_6_2_your_decision_record_passes_the_lint():
    adr = sections(read_doc("decisions/ADR-001-investigator-tier.md"))
    record = {"decision": adr.get("Decision"), "why": adr.get("Why"), "gives_up": adr.get("What it gives up"),
              "alternatives": adr.get("Alternatives considered")}
    assert lint_decision(record) == []
    assert len(record["alternatives"].splitlines()) >= 2, "name more than one rejected alternative"
    execs = adr.get("For executives", "").lower()
    assert execs and not [j for j in JARGON if re.search(rf"\b{j}\b", execs)], "executive summary without jargon"


# ====================================================================== 6.3 Documentation, handoff, life cycle


def test_6_3_runbook_covers_every_alert():
    runbook = read_doc("RUNBOOK.md")
    for alert in monitoring.ALERTS:
        assert f"`{alert}`" in runbook, f"which failure mode does {alert} mean, and what do we do?"


def test_6_3_runbook_maps_every_trigger_to_its_queue_and_role():
    lines = read_doc("RUNBOOK.md").splitlines()
    for trigger in escalation.TRIGGERS:
        queue, role = escalation.QUEUES[trigger]
        row = next((ln for ln in lines if f"`{trigger}`" in ln and ln.lstrip().startswith("|")), None)
        assert row, f"no table row for {trigger}"
        assert queue in row and role in row, f"{trigger}: name its queue ({queue}) and role ({role})"


def test_6_3_runbook_says_an_auth_outage_is_a_denial():
    text = read_doc("RUNBOOK.md").lower()
    assert re.search(r"authori[sz]ation[^.\n]*outage|outage[^.\n]*authori[sz]ation", text)
    assert "denial" in text and "fail secure" in text


def test_6_3_handoff_has_an_owner_and_an_update_trigger():
    text = read_doc("HANDOFF.md")
    owner = re.search(r"(?m)^Owner:\s*(.+)$", text)
    trigger = re.search(r"(?m)^Update trigger:\s*(.+)$", text)
    assert owner and len(owner.group(1).split()) >= 2, "stale docs are worse than none: name an owner"
    assert trigger and len(trigger.group(1).split()) >= 4, "tie updates to the event that changes the system"


def test_6_3_handoff_carries_the_discovery_thread():
    text = read_doc("HANDOFF.md")
    for item in [r.id for r in REQUIREMENTS] + [c.id for c in CONSTRAINTS]:
        assert re.search(rf"\b{item}\b", text), f"{item} from discovery is missing from the handoff"


def test_6_3_handoff_service_levels_are_measurable():
    levels = sections(read_doc("HANDOFF.md"))
    body = next(v for k, v in levels.items() if k.lower().startswith("3. service levels"))
    bullets = [ln[2:] for ln in body.splitlines() if ln.startswith("- ")]
    assert len(bullets) >= 5
    assert all(is_measurable(b) for b in bullets), [b for b in bullets if not is_measurable(b)]


def test_6_3_handoff_records_why_for_every_component():
    lines = read_doc("HANDOFF.md").splitlines()
    for component in ("intake", "policy_check", "drafting", "investigation", "decision"):
        row = next((ln for ln in lines if ln.startswith(f"| {component} ")), None)
        assert row, f"no architecture row for {component}"
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) >= 4 and len(cells[-1].split()) >= 8, f"{component}: record WHY, not just what"
        tier = design.TASK_DESIGN[component].model or "none"
        assert tier in row, f"{component}: the tier in the handoff must match design.TASK_DESIGN ({tier})"
