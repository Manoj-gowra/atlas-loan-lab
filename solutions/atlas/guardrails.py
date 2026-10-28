"""LAB 5 - Exercise 5.1: guardrails as layered defence, failing SECURE.

Course lesson 5.1. Three guardrail points, each catching what the others can't:
  INPUT screening   - injected instructions and sensitive data before anything reaches the model
  OUTPUT screening  - prohibited factors and leaked data before anyone sees or acts on the output
  TOOL-CALL authorization - the gate from Lab 3 (gate.py)
A guardrail is enforced independently of what the model decides; a system prompt saying "be safe"
is guidance. And when a guardrail itself fails (outage, timeout), it fails SECURE: block or hold,
never pass the request through as if it had been checked.

APP-008 carries an INDIRECT prompt injection: the attacker is whoever wrote the document, not the
person using the system. Defence: treat document text as data, screen it, and keep the component
that reads it away from privileged tools (intake has no data tools - privilege separation).

Until you do Lab 5, the STARTER versions here are pass-throughs so earlier labs run.
"""
from __future__ import annotations

import re
from typing import Callable

PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "DOB": r"(?i)\b(?:date of birth|dob)\s*:?\s*\d{4}-\d{2}-\d{2}",
    "ADDRESS": r"(?im)^\s*(?:home address|home)\s*:[^\n]*",
    "EMAIL": r"\b[\w.+-]+@[\w-]+\.[\w.]+\b",
    "PHONE": r"(?:\(\d{3}\)\s?|\b\d{3}[-.\s])\d{3}[-.\s]\d{4}\b",
}
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"note to the ai",
    r"you are now",
    r"(reveal|print|show) (your|the) system prompt",
    r"set the recommendation",
    r"skip (all )?(the )?(credit )?checks",
    r"pre-?approved",
]
PROHIBITED_FACTORS = {
    "age": r"\bage\b|\byears old\b|\belderly\b|\bretirement age\b",
    "marital status": r"\bmarital\b|\bmarried\b|\bdivorced?\b|\bwidowed\b",
    "race or colour": r"\brace\b|\bracial\b|\bethnicity\b|\bskin colou?r\b",
    "religion": r"\breligio\w*\b|\bchurch\b|\bmosque\b|\bsynagogue\b|\btemple\b",
    "national origin": r"\bnational origin\b|\bimmigrant\b|\bforeign[- ]born\b|\bnationality\b",
    "sex": r"\bgender\b|\bpregnan\w*\b",
    "public assistance": r"\bwelfare\b|\bfood stamps\b|\bpublic assistance\b",
}
LEAK_PATTERNS = {"pii": r"\b\d{3}-\d{2}-\d{4}\b", "system_prompt": r"(?i)you are the (policy explainer|intake assistant)"}


def redact_pii(text: str) -> str:
    """Replace every PII_PATTERNS match with "[<LABEL>]" (e.g. "[SSN]"), in dict order."""
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[{label}]", text)
    return text


def screen_document(text: str) -> tuple[str, list[str]]:
    """Replace each LINE matching any INJECTION_PATTERNS (case-insensitive) with
    "[removed: suspected prompt injection]". Return (clean_text, ["prompt_injection"] or [])."""
    clean, hit = [], False
    for line in text.splitlines():
        if any(re.search(p, line, re.I) for p in INJECTION_PATTERNS):
            clean.append("[removed: suspected prompt injection]")
            hit = True
        else:
            clean.append(line)
    return "\n".join(clean), (["prompt_injection"] if hit else [])


def fail_secure(check: Callable[[str], tuple[str, list[str]]], text: str) -> tuple[str, list[str]]:
    """Run a screening check. If the check itself raises (the screening service is down), do NOT pass
    the text through as screened: return ("", ["screening_unavailable"]) so the case is held."""
    try:
        return check(text)
    except Exception:
        return "", ["screening_unavailable"]


def screen_input(raw: str, check: Callable[[str], tuple[str, list[str]]] | None = None) -> tuple[str, list[str]]:
    """Given: input screening = injection screening (failing secure) + PII redaction before the model."""
    text, flags = fail_secure(check or screen_document, raw)
    return redact_pii(text), flags


def find_prohibited_factors(text: str) -> list[str]:
    """Sorted names of PROHIBITED_FACTORS mentioned in a model output (case-insensitive). No false
    positives on "average", "page", "mortgage" or "single"."""
    return sorted(name for name, pattern in PROHIBITED_FACTORS.items() if re.search(pattern, text, re.I))


def screen_output(text: str) -> list[str]:
    """Output screening flags: "prohibited_factor:<name>" for each prohibited factor, then
    "leak:<kind>" for each LEAK_PATTERNS match."""
    flags = [f"prohibited_factor:{name}" for name in find_prohibited_factors(text)]
    flags += [f"leak:{kind}" for kind, pattern in LEAK_PATTERNS.items() if re.search(pattern, text)]
    return flags
