"""LAB 4 - Exercise 4.4: optimizing cost, latency and performance - AFTER correctness.

Course lesson 4.4. A wrong answer produced faster and cheaper is not an improvement. Read the same
traces you built for regressions, but ask a different question: what is being PAID for and never
used? Three levels: token (unneeded context), call (reasoning a task doesn't need), architecture
(synchronous where nobody waits; an expensive step for every case when only a flagged subset needs it).
"""
from __future__ import annotations

from typing import Any

from . import config
from .design import SLOs
from .evals import check_slos


def find_waste(cases: list[Any], stable_prefix_tasks: tuple[str, ...] = ("intake", "policy_check")) -> dict[str, Any]:
    """From processed CaseFiles:
      "cache_miss_rate": {task: share of that task's LLM calls whose attrs["cache"] != "hit"} for each
                         stable-prefix task that has calls (rounded 4 dp)
      "retrieval_utilization": cited chunk ids / retrieved chunk ids, summed over cases that have an
                         explanation (len(explanation.citations) / len(explanation.chunk_ids)), rounded 4 dp,
                         0.0 when nothing was retrieved
    """
    miss = {}
    for task in stable_prefix_tasks:
        calls = [s for c in cases if c.trace for s in c.trace.llm_calls(task)]
        if calls:
            miss[task] = round(sum(1 for s in calls if s.attrs.get("cache") != "hit") / len(calls), 4)
    cited = sum(len(c.explanation.citations) for c in cases if c.explanation)
    retrieved = sum(len(c.explanation.chunk_ids) for c in cases if c.explanation)
    return {"cache_miss_rate": miss, "retrieval_utilization": round(cited / retrieved, 4) if retrieved else 0.0}


def processing_plan(n_applications: int, cost_per_application: float, someone_waiting: bool) -> dict[str, Any]:
    """Batch vs synchronous for a job. If someone is waiting in real time -> synchronous at full cost.
    Otherwise (a deadline, not a wait - e.g. nightly screening due before the morning shift) ->
    batch at (1 - config.BATCH_DISCOUNT) of the cost.
    Return {"mode", "total_cost", "savings"} (money rounded to 2 dp)."""
    full = n_applications * cost_per_application
    if someone_waiting:
        return {"mode": "synchronous", "total_cost": round(full, 2), "savings": 0.0}
    batch = full * (1 - config.BATCH_DISCOUNT)
    return {"mode": "batch", "total_cost": round(batch, 2), "savings": round(full - batch, 2)}


def accept_optimization(before: dict, after: dict, slos: SLOs) -> bool:
    """Ship an optimization only if the variant AFTER it still meets every SLO and its overall field
    and route accuracy did not drop compared with BEFORE (re-verify on the same dataset)."""
    ok = all(check_slos(after, slos).values())
    a, b = after["overall"], before["overall"]
    return ok and a["field_accuracy"] >= b["field_accuracy"] and a["route_accuracy"] >= b["route_accuracy"]
