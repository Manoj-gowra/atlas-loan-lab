"""LAB 3 - Exercise 3.6: observability and monitoring at scale.

Course lesson 3.6. LLM systems fail in ways uptime dashboards can't see:
  non-determinism        - a clean retry does not prove there was no problem
  silent regressions     - stale index, changed document format: no errors, plausible output
  cost drift             - a broken cache prefix quietly doubles spend
So: trace the details (tracing.py), STRATIFY metrics (an aggregate hides a 60% format inside a
94% average), and alert on the signals that actually move - a rising correction rate on ONE field,
a falling cache hit rate, cost per call drifting up.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable

from .tracing import Trace

ALERTS = ("correction_rate_spike", "cache_hit_rate_drop", "cost_per_call_drift")  # see docs/RUNBOOK.md


def cache_hit_rate(traces: Iterable[Trace], task: str) -> float:
    """Share of `task` LLM calls whose span attrs["cache"] == "hit" (0.0 when there are none)."""
    # TODO (Lab 3): Collect llm spans for the task across traces; hits / total.
    raise NotImplementedError("Lab 3: implement cache_hit_rate()")


def stratify(items: Iterable[Any], key: Callable[[Any], str], value: Callable[[Any], float]) -> dict[str, float]:
    """Average of value(item) per key(item), rounded to 4 decimals - the dashboard that cannot hide a
    weak category inside a healthy average."""
    # TODO (Lab 3): Group with a defaultdict(list), then average each group.
    raise NotImplementedError("Lab 3: implement stratify()")


def evaluate_alerts(signals: dict[str, Any], baselines: dict[str, Any], factor: float = 2.0) -> list[str]:
    """Which ALERTS fire.
      correction_rate_spike: any field in signals["correction_rate_by_field"] whose rate exceeds
                             factor x its baseline in baselines["correction_rate_by_field"]
                             (missing baseline counts as 0.02)
      cache_hit_rate_drop:   signals["cache_hit_rate"] < baselines["cache_hit_rate"] / factor
      cost_per_call_drift:   signals["cost_per_call"] > baselines["cost_per_call"] * factor
    Return fired alert ids in ALERTS order. Missing signals simply don't fire."""
    # TODO (Lab 3): Three independent checks guarded by "key in signals".
    raise NotImplementedError("Lab 3: implement evaluate_alerts()")


def should_close_ticket(retry_succeeded: bool, similar_reports_last_30_days: int) -> bool:
    """Non-determinism: a successful retry alone never closes a quality ticket. Close only when the
    retry succeeded AND no similar report exists in the last 30 days (no pattern)."""
    # TODO (Lab 3): Both conditions.
    raise NotImplementedError("Lab 3: implement should_close_ticket()")
