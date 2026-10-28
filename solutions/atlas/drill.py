"""The Lab 8 incident drill (course capstone, case 2). GIVEN FILE - run it with scripts/incident_drill.py.

Timeline it reproduces (a separate sandbox under runs/drill/, your real data is untouched):
  2026-10-27 02:00  nightly index build from the policy folder
  2026-10-28 16:00  Compliance publishes POL-AGEQ v4: DSCR minimum 1.20 -> 1.35 from 2026-11-01
                    (the RULEBOOK change shipped weeks earlier, ahead of the effective date)
  2026-10-29 02:00  nightly index build SKIPPED (job runner out of disk) - nobody notices
  2026-11-03..05    three agricultural equipment applications arrive
The rules engine applies v4; retrieval still returns v3; explanations cite the old 1.20 threshold.
No error anywhere. The average judge score barely moves. One loan type is wrong.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any

from . import config, data_access, llm, rag
from .capstone import citation_conflicts
from .evals import load_golden
from .judge import judge_explanation
from .pipeline import CaseFile, process_application

DRILL_APPS = ["APP-101", "APP-102", "APP-103"]
TIMELINE = [
    {"ts": "2026-10-27T02:00:00+00:00", "what": "index: nightly build from policies (ok)"},
    {"ts": "2026-10-28T16:00:00+00:00", "what": "policy: POL-AGEQ v4 published (DSCR minimum 1.35 from 2026-11-01)"},
    {"ts": "2026-10-29T02:00:00+00:00", "what": "index: nightly build SKIPPED (job runner out of disk)"},
]
REGRESSION_START = "2026-11-03T09:00:00+00:00"


def sandbox() -> None:
    """Point RUNS and the policy folder at runs/drill/ so the drill never touches your real runs."""
    config.RUNS = config.ROOT / "runs" / "drill"
    os.environ["ATLAS_POLICY_DIR"] = str(config.RUNS / "policies")


def setup_before_update() -> rag.PolicyIndex:
    """Fresh sandbox with the current policies, plus the nightly build of 2026-10-27."""
    shutil.rmtree(config.RUNS, ignore_errors=True)
    shutil.copytree(config.DATA / "policies", config.policy_dir())
    with open(config.RUNS / "change_log.jsonl", "w") as f:
        f.write(json.dumps(TIMELINE[0]) + "\n")
    return rag.refresh_index("nightly build 2026-10-27")


def publish_v4() -> None:
    """Compliance publishes v4 and closes v3 - but the index is NOT rebuilt."""
    folder = config.policy_dir()
    shutil.copy(config.DATA / "drills" / "policies" / "ag_equipment_v4.md", folder / "ag_equipment_v4.md")
    v3 = folder / "ag_equipment_v3.md"
    v3.write_text(v3.read_text().replace("effective_to: null", "effective_to: 2026-10-31"))
    with open(config.RUNS / "change_log.jsonl", "a") as f:
        for entry in TIMELINE[1:]:
            f.write(json.dumps(entry) + "\n")


def change_log() -> list[dict]:
    path = config.RUNS / "change_log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def run_cases(app_ids: list[str]) -> dict[str, CaseFile]:
    llm.reset_client()
    data_access.reset_simulations()
    return {a: process_application(a) for a in app_ids}


def scorecard(cases: dict[str, CaseFile]) -> dict[str, dict[str, Any]]:
    """Per loan type: share of cases with citation conflicts, and the judge's pass rate."""
    golden = {row["app_id"]: row for row in load_golden()}
    golden.update({row["app_id"]: row for row in load_golden(config.DATA / "drills" / "golden_drill.jsonl")})
    by_type: dict[str, list] = {}
    for app_id, case in cases.items():
        if case.rule_report is None or case.explanation is None:
            continue
        verdict = judge_explanation(case.rule_report, case.explanation.text)
        by_type.setdefault(golden[app_id]["loan_type"], []).append(
            (bool(citation_conflicts(case.rule_report, case.explanation)), bool(verdict.get("passed"))))
    return {t: {"n": len(v), "citation_conflict_rate": round(sum(c for c, _ in v) / len(v), 3),
                "judge_pass_rate": round(sum(p for _, p in v) / len(v), 3)} for t, v in sorted(by_type.items())}
