"""LAB 2 - Exercises 2.3 and 2.4: prompting technique, instruction hierarchy, modular prompts.

2.3 System Prompts, Guardrails, and Prompting Technique
    - Technique to task: zero-shot (simple, well specified), few-shot (idiosyncratic, easier to
      show than describe, HARD boundary examples), chain-of-thought (multi-step, or when the
      reasoning itself is the deliverable).
    - Instruction hierarchy: the SYSTEM prompt holds what is stable (role, boundaries, format,
      edge cases); the USER message holds the per-request document; the TOOL SCHEMA holds structural
      constraints. A system prompt containing one applicant's details is a template that was never
      separated from its variable content (and it breaks caching - 2.4).
2.4 Context Windows, Prompt Caching, and Reuse
    - Modular prompts: shared instruction modules written once and included everywhere
      ({{include: shared/<name>}}), like Skills - one fix updates every component.
"""
from __future__ import annotations

import re
from typing import Callable

TECHNIQUE: dict[str, str] = {
    "risk_tier_triage": "zero_shot",   # three well-established tiers, simple criteria
    "intake": "few_shot",              # messy forms: boundary cases are easier to show than describe
    "policy_check": "chain_of_thought",  # the officer and the regulator need the WHY, not just a label
}

INCLUDE_RE = re.compile(r"\{\{include:\s*([\w/\-]+)\s*\}\}")


def compose(text: str, load: Callable[[str], str], _seen: tuple[str, ...] = ()) -> str:
    """Replace every {{include: name}} with load(name), recursively (included modules may include
    others). Raise ValueError on a cycle (a module that ends up including itself)."""
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name in _seen:
            raise ValueError(f"include cycle: {' -> '.join(_seen + (name,))}")
        return compose(load(name), load, _seen + (name,))

    return INCLUDE_RE.sub(replace, text)


PER_REQUEST_PATTERNS = {
    "application id": r"\bAPP-\d{3}\b",
    "customer id": r"\bB-\d{4}\b",
    "specific date": r"\b20\d\d-\d\d-\d\d\b",
}
EDGE_CASE_WORDS = ("missing", "illegible", "unreadable", "blank")


def lint_system_prompt(text: str) -> list[str]:
    """Problems that make a system prompt a demo prompt rather than a production one.

    - one problem string per PER_REQUEST_PATTERNS label found: "per-request content: <label>"
    - "no edge-case handling" if none of EDGE_CASE_WORDS appears (case-insensitive)
    Return [] when the prompt is clean.
    """
    problems = [f"per-request content: {label}" for label, pat in PER_REQUEST_PATTERNS.items() if re.search(pat, text)]
    if not any(w in text.lower() for w in EDGE_CASE_WORDS):
        problems.append("no edge-case handling")
    return problems
