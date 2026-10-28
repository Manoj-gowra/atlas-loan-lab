"""Lab 8 incident drill: the stale-index near miss from the course capstone.

    python scripts/incident_drill.py            # steps 1-3: reproduce, detect, diagnose
    python scripts/incident_drill.py --fix      # also step 4: fix and verify
    add --solution to run against the reference implementation
Everything happens in runs/drill/; your real data and runs are untouched.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solutions" if "--solution" in sys.argv else ROOT))

from atlas import config, diagnosis, drill, rag  # noqa: E402
from atlas.capstone import citation_conflicts  # noqa: E402

drill.sandbox()
print("STEP 1  Reproduce: nightly index build, then Compliance publishes POL-AGEQ v4 (index NOT rebuilt)")
drill.setup_before_update()
drill.publish_v4()
cases = drill.run_cases(["APP-001", "APP-006", "APP-009"] + drill.DRILL_APPS)

print("\nSTEP 2  Detect: stratify by loan type (the average hides it)")
for loan_type, row in drill.scorecard(cases).items():
    print(f"  {loan_type:<14} n={row['n']}  citation conflicts {row['citation_conflict_rate']:.0%}   judge pass {row['judge_pass_rate']:.0%}")
for app_id in drill.DRILL_APPS:
    c = cases[app_id]
    print(f"  {app_id}: rules engine applied {c.rule_report.rules_version}; explanation cites {c.explanation.citations}")
    print(f"           triggers={c.triggers} citation_conflicts={citation_conflicts(c.rule_report, c.explanation)}")

print("\nSTEP 3  Diagnose: what changed right before the regression started?")
print("  change:", diagnosis.what_changed(drill.change_log(), drill.REGRESSION_START, window_hours=168))
index = rag.get_index()
print(f"  index built_at={index.built_at}  stale={index.is_stale(config.policy_dir())}")

if "--fix" in sys.argv:
    print("\nSTEP 4  Fix and verify: rebuild the index, re-run the SAME stratified check")
    rag.refresh_index("post-incident rebuild")
    after = drill.run_cases(["APP-001", "APP-006", "APP-009"] + drill.DRILL_APPS)
    for loan_type, row in drill.scorecard(after).items():
        print(f"  {loan_type:<14} n={row['n']}  citation conflicts {row['citation_conflict_rate']:.0%}   judge pass {row['judge_pass_rate']:.0%}")
    print("\nSTEP 5  Communicate and document: write docs/incident_note.md from what you just saw")
