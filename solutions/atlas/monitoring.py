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
    calls = [s for t in traces for s in t.llm_calls(task)]
    return round(sum(1 for s in calls if s.attrs.get("cache") == "hit") / len(calls), 4) if calls else 0.0


def stratify(items: Iterable[Any], key: Callable[[Any], str], value: Callable[[Any], float]) -> dict[str, float]:
    """Average of value(item) per key(item), rounded to 4 decimals - the dashboard that cannot hide a
    weak category inside a healthy average."""
    groups: dict[str, list[float]] = defaultdict(list)
    for item in items:
        groups[key(item)].append(value(item))
    return {k: round(sum(v) / len(v), 4) for k, v in groups.items()}


def evaluate_alerts(signals: dict[str, Any], baselines: dict[str, Any], factor: float = 2.0) -> list[str]:
    """Which ALERTS fire.
      correction_rate_spike: any field in signals["correction_rate_by_field"] whose rate exceeds
                             factor x its baseline in baselines["correction_rate_by_field"]
                             (missing baseline counts as 0.02)
      cache_hit_rate_drop:   signals["cache_hit_rate"] < baselines["cache_hit_rate"] / factor
      cost_per_call_drift:   signals["cost_per_call"] > baselines["cost_per_call"] * factor
    Return fired alert ids in ALERTS order. Missing signals simply don't fire."""
    fired = []
    rates = signals.get("correction_rate_by_field", {})
    base_rates = baselines.get("correction_rate_by_field", {})
    if any(rate > factor * base_rates.get(f, 0.02) for f, rate in rates.items()):
        fired.append("correction_rate_spike")
    if "cache_hit_rate" in signals and signals["cache_hit_rate"] < baselines.get("cache_hit_rate", 0) / factor:
        fired.append("cache_hit_rate_drop")
    if "cost_per_call" in signals and signals["cost_per_call"] > baselines.get("cost_per_call", float("inf")) * factor:
        fired.append("cost_per_call_drift")
    return fired


def should_close_ticket(retry_succeeded: bool, similar_reports_last_30_days: int) -> bool:
    """Non-determinism: a successful retry alone never closes a quality ticket. Close only when the
    retry succeeded AND no similar report exists in the last 30 days (no pattern)."""
    return retry_succeeded and similar_reports_last_30_days == 0
