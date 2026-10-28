"""LAB 7 - Exercises 7.1 and 7.2: team tooling and AI-assisted debugging.

7.1 Configuring Claude Tooling for Teams: package a repeated team task ONCE as a reusable workflow so
    every engineer gets the same, scannable result. Atlas's example: run the test suite and summarize
    failures BY CATEGORY. summarize_failures() is the engine behind the test-summary skill.
7.2 AI-Assisted Workflows and Operational Debugging: an assistant speeds up FORMING a hypothesis, not
    confirming it. A confident root-cause story from code alone is a plausible guess until it is
    checked against what actually happened - the traces. verify_hypothesis() does that check.
"""
from __future__ import annotations

import re
from typing import Any

LINE_RE = re.compile(r"^(FAILED|ERROR)\s+tests/test_(lab\d)\.py::(\w+)")


def summarize_failures(pytest_output: str) -> dict[str, list[str]]:
    """Parse the short summary lines pytest prints with -rfE, e.g.
        "FAILED tests/test_lab3.py::test_gate_fails_secure - AssertionError: ..."
    and return {"lab3": ["test_gate_fails_secure", ...], ...} - labs in sorted order, tests in the
    order they appear. Lines that don't match are ignored."""
    out: dict[str, list[str]] = {}
    for line in pytest_output.splitlines():
        m = LINE_RE.match(line.strip())
        if m:
            out.setdefault(m.group(2), []).append(m.group(3))
    return dict(sorted(out.items()))


def verify_hypothesis(hypothesis: dict[str, Any], spans: list[dict]) -> dict[str, Any]:
    """Check an assistant's root-cause claim against trace evidence.

    hypothesis = {"claim": str, "evidence": [{"span": name, "attr": key, "equals": value}, ...]}
    spans = a loaded trace (tracing.load_trace). An evidence item is SUPPORTED when at least one span
    with that name has attrs[attr] == equals. Return {"verified": all supported (and evidence non-empty),
    "supported": [items], "unsupported": [items]}. No evidence at all = not verified (a claim, not a diagnosis)."""
    supported, unsupported = [], []
    for item in hypothesis.get("evidence", []):
        ok = any(s.get("name") == item["span"] and s.get("attrs", {}).get(item["attr"]) == item["equals"] for s in spans)
        (supported if ok else unsupported).append(item)
    return {"verified": bool(supported) and not unsupported, "supported": supported, "unsupported": unsupported}
