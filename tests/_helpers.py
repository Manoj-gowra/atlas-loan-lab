"""Shared helpers for the lab tests (not a test file)."""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from types import SimpleNamespace


@lru_cache(maxsize=None)
def _golden() -> dict:
    from atlas import config

    rows = {}
    for path in (config.DATA / "golden" / "golden.jsonl", config.DATA / "drills" / "golden_drill.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["app_id"]] = row
    return rows


def gold(app_id: str) -> dict:
    return _golden()[app_id]


def app_from_gold(app_id: str, submitted_on: date = date(2026, 9, 15), **overrides):
    """A LoanApplication with the CORRECT values from the golden set (no model involved)."""
    from atlas.schemas import LoanApplication

    fields = dict(gold(app_id)["expected_fields"])
    fields.update(purpose="test", submitted_on=submitted_on)
    fields.update(overrides)
    return LoanApplication(**fields)


def process(app_id: str, **kwargs):
    from atlas.pipeline import process_application

    return process_application(app_id, **kwargs)


def fake_client():
    from atlas import llm

    return llm.get_client()


def usage(input_tokens=0, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0):
    return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens,
                           cache_creation_input_tokens=cache_creation_input_tokens,
                           cache_read_input_tokens=cache_read_input_tokens)
