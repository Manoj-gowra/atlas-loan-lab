"""Project settings: paths, run mode, model IDs and prices.

GIVEN FILE - read it once; you don't need to change it.
Course link: 2.1 Selecting the Right Claude Model (IDs and prices live in ONE place).
"""
from __future__ import annotations

import os
from pathlib import Path


def _find_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "applications").is_dir():
            return parent
    raise RuntimeError("Could not find the project root (a folder containing data/applications).")


ROOT = _find_root()
DATA = ROOT / "data"
RUNS = ROOT / "runs"  # everything the system writes: traces, audit log, queues, index, feedback
# The folder holding this package: the project root for your code, solutions/ for the reference.
WORKSPACE = Path(__file__).resolve().parent.parent
PROMPTS = WORKSPACE / "prompts"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def mode() -> str:
    """'fake' (offline, free, deterministic) or 'anthropic' (real Claude API)."""
    return os.getenv("ATLAS_MODE", "fake").lower()


def policy_dir() -> Path:
    """Where the lending policies live. The Lab 8 incident drill points this at a copy."""
    return Path(os.getenv("ATLAS_POLICY_DIR", str(DATA / "policies")))


# Short names -> API model IDs. Checked against platform.claude.com/docs/en/models/overview on 2026-10-13.
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}

# USD per million tokens, checked 2026-10-13 (verify before quoting). Haiku: prompts up to 100K tokens.
PRICES = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read_mult": 0.10},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read_mult": 0.05},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read_mult": 0.05},
}
CACHE_WRITE_MULT = 1.25   # 5-minute cache writes cost 1.25x base input (1-hour writes cost 2x)
BATCH_DISCOUNT = 0.50     # Message Batches API: 50% off input and output
MIN_CACHEABLE_TOKENS = 1024  # the fake's minimum; real minimums vary by model
