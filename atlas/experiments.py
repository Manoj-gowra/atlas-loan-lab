"""LAB 4 - Exercise 4.2: A/B testing and iterative improvement.

Course lesson 4.2:
  - Isolate ONE variable. Change the prompt and the model together and you learn nothing about either.
  - Enough data: a modest difference on a handful of cases can be ordinary variance. Stratify the
    comparison set like the eval set. (Our 10 golden cases teach the mechanics; the fake model is
    deterministic so variance is zero here - with real Claude you'd need far more cases and repeats.)
  - Specific feedback beats "be more accurate" (see extraction.validation_feedback).
  - Close the loop: re-run the SAME dataset after a targeted fix before trusting it.
"""
from __future__ import annotations

from typing import Any, Callable


def differing_variables(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Sorted keys (from both configs) whose values differ (a missing key counts as different)."""
    # TODO (Lab 4): Union of keys, compare .get values.
    raise NotImplementedError("Lab 4: implement differing_variables()")


def assert_single_variable(a: dict[str, Any], b: dict[str, Any]) -> str:
    """Return the one variable under test; ValueError if zero or more than one differ."""
    # TODO (Lab 4): Use differing_variables.
    raise NotImplementedError("Lab 4: implement assert_single_variable()")


def undersized_strata(counts: dict[str, int], minimum: int = 30) -> list[str]:
    """Sorted strata with fewer than `minimum` cases - too few to trust a modest difference."""
    # TODO (Lab 4): Filter and sort.
    raise NotImplementedError("Lab 4: implement undersized_strata()")


def run_ab(config_a: dict[str, Any], config_b: dict[str, Any], evaluate: Callable[..., dict]) -> dict[str, Any]:
    """Given: guard the design, then run the SAME evaluation for both variants."""
    variable = assert_single_variable(config_a, config_b)
    return {"variable": variable, "a": evaluate(**config_a), "b": evaluate(**config_b)}
