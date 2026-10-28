"""LAB 4 - Exercise 4.1 (mixed methodology): an LLM-as-judge, calibrated by human review.

Course lesson 4.1. Policy explanations have no single correct string, so exact match can't score
them. An LLM judge can - IF its criteria are clear, specific and OBSERVABLE (not "rate the quality").
Human review is too slow for every case, so it does something else: it CALIBRATES the judge.
data/golden/judge_labels.jsonl holds five human verdicts. Measure agreement; where the judge and the
humans disagree, the rubric is missing a criterion the humans care about. Add it and re-measure.
"""
from __future__ import annotations

import json
from typing import Any

from . import config, llm

JUDGE_TOOL = {
    "name": "record_judgment",
    "description": "Record the verdict for each criterion and whether the explanation passed overall.",
    "input_schema": {"type": "object", "properties": {
        "criteria": {"type": "object", "additionalProperties": {"type": "boolean"}},
        "passed": {"type": "boolean"}, "notes": {"type": "string"}}, "required": ["criteria", "passed"]},
}

CRITERIA: list[tuple[str, str]] = [
    # ("names_flagged_rules", "Every rule that did not pass is named in the explanation."),
    # TODO: add the observable criteria, then calibrate with judge_labels.jsonl
]


def load_labels() -> list[dict]:
    path = config.DATA / "golden" / "judge_labels.jsonl"
    return [json.loads(line) for line in open(path) if line.strip()]


def judge_explanation(report: Any, explanation_text: str, criteria: list[tuple[str, str]] | None = None) -> dict:
    """Score one explanation. System = llm.build_system(llm.load_prompt("judge") + rubric) where the
    rubric lists each criterion as '<criterion id="ID">DESCRIPTION</criterion>' (stable -> cached).
    User message: '<rule_results>' + JSON of each result's __dict__ + '</rule_results>' and
    '<explanation>' + text + '</explanation>'. Force the record_judgment tool and return its input dict."""
    # TODO (Lab 4): Build the rubric and the message, call llm.call("judge", ...) with a forced tool, return
    #   the tool input.
    raise NotImplementedError("Lab 4: implement judge_explanation()")


def agreement(verdicts: dict[str, bool], labels: list[dict]) -> float:
    """Share of labelled app_ids where verdicts[app_id] == label["human_pass"] (labels without a
    verdict are skipped; 0.0 when nothing overlaps), rounded to 4 decimals."""
    # TODO (Lab 4): Compare over the overlap.
    raise NotImplementedError("Lab 4: implement agreement()")
