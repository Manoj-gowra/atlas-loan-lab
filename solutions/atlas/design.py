"""LAB 1 - Solution design and architecture (course Chapter 1, 17% of the exam).

Exercises in this file, in course order:
  1.1 From Business Problem to Solution Architecture -> DECOMPOSITION, officer_hours_saved,
      max_cost_per_application, SLOS
  1.2 Choosing the Architecture Pattern             -> choose_pattern, TASK_DESIGN
  1.3 Multi-Agent Systems and Orchestration         -> needs_coordinator (provenance is in coordination.py)
  1.4 Reference Architectures and Feedback Loops    -> reference_architecture (feedback records in feedback.py)

Read docs/discovery_notes.md first: the mandate, the numbers and the stakeholders are there.
`llm.choose_model()` reads TASK_DESIGN, so this table really drives the system.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ------------------------------------------------------------------ 1.1 decomposition


@dataclass(frozen=True)
class Task:
    name: str
    input: str
    output: str
    risk: str            # "low" | "medium" | "high"
    reversible: bool     # can a wrong output be caught and corrected before harm?
    moves_metric: str    # "yes" | "partly" | "no"  (does it cut officer time per application?)
    disposition: str     # "automate" | "assist" | "human"


DECOMPOSITION: list[Task] = [
    Task("intake", "uploaded PDFs (statements, tax returns, debt schedules)", "structured application fields",
         "low", True, "yes", "automate"),
    Task("policy_check", "structured fields + lending policy", "pass/borderline/fail per rule, cited",
         "medium", True, "yes", "automate"),
    Task("drafting", "structured application + rule results", "draft credit memo the officer edits",
         "medium", True, "partly", "assist"),
    Task("decision", "everything above", "approve or decline", "high", False, "no", "human"),
]


def officer_hours_saved(minutes_per_app: float, apps_per_year: int, share_removed: float) -> float:
    """Hours of officer time returned per year (the number that gets a project funded)."""
    return minutes_per_app * apps_per_year * share_removed / 60


def max_cost_per_application(hours_saved: float, loaded_hourly_cost: float, apps_per_year: int) -> float:
    """The running-cost ceiling per application: the value created, spread over the applications.
    A design that costs more than this per application destroys the business case."""
    return hours_saved * loaded_hourly_cost / apps_per_year


@dataclass(frozen=True)
class SLOs:
    """Measurable targets agreed with the business (value pillar: performance and SLAs)."""
    p95_case_ready_s: float     # 95% of case files ready within this many seconds of upload
    max_avg_cost_usd: float     # average model spend per application
    min_field_accuracy: float   # per document type, not just overall (0-1)
    min_route_accuracy: float   # approve / decline / investigate routing (0-1)
    max_review_rate: float      # share of applications needing an officer field check (0-1)


SLOS = SLOs(p95_case_ready_s=60, max_avg_cost_usd=0.05, min_field_accuracy=0.95,
            min_route_accuracy=0.90, max_review_rate=0.30)

# ------------------------------------------------------------------ 1.2 pattern selection


class Pattern(str, Enum):
    AUGMENTED_LLM = "augmented_llm"  # one bounded call + retrieval/tools/memory as needed
    WORKFLOW = "workflow"            # predefined path: chaining, routing, parallelization
    AGENT = "agent"                  # the model decides the next step at runtime
    HUMAN = "human"                  # a person decides; the system prepares


def choose_pattern(single_bounded_call: bool, flowchart_known: bool) -> Pattern:
    """The course's decision framework: stop at the FIRST yes.
    1. Can it be one bounded call?           -> AUGMENTED_LLM
    2. Can you draw the full flowchart?      -> WORKFLOW (routing among known options is still a workflow)
    3. Otherwise (path depends on results)   -> AGENT
    """
    if single_bounded_call:
        return Pattern.AUGMENTED_LLM
    if flowchart_known:
        return Pattern.WORKFLOW
    return Pattern.AGENT


@dataclass(frozen=True)
class TaskDesign:
    pattern: Pattern
    model: str | None   # "haiku" | "sonnet" | "opus" | None
    why: str            # one sentence you could say in an interview


TASK_DESIGN: dict[str, TaskDesign] = {
    "intake": TaskDesign(Pattern.AUGMENTED_LLM, "haiku",
                         "One document in, one schema out: a single bounded call on a compact model, verified on messy scans."),
    "policy_check": TaskDesign(Pattern.WORKFLOW, "sonnet",
                               "The steps never change: retrieve the sections, check rules in code, then explain with citations."),
    "drafting": TaskDesign(Pattern.WORKFLOW, "sonnet",
                           "A fixed path assembles the facts, drafts the memo and screens it; the officer edits every word."),
    "investigation": TaskDesign(Pattern.AGENT, "opus",
                                "Where to look depends on what is found, volume is low and a shallow answer is costly."),
    "decision": TaskDesign(Pattern.HUMAN, None,
                           "Approving or declining credit is high impact, irreversible and regulated, so an authorized person decides."),
}

# Given: the LLM judge used in Lab 4 (lesson 4.1).
TASK_DESIGN["judge"] = TaskDesign(Pattern.AUGMENTED_LLM, "sonnet",
                                  "Scoring an explanation against fixed, observable criteria is one bounded call.")

# ------------------------------------------------------------------ 1.3 multi-agent


def needs_coordinator(independent_subtasks: bool, tool_count: int, context_polluted: bool) -> bool:
    """The three signals that justify a coordinator with specialists. Any one is enough:
    independent parallelizable subtasks; tool-count overload (more than 5 tools for one agent);
    context pollution from exploring several angles in one session."""
    return independent_subtasks or tool_count > 5 or context_polluted

# ------------------------------------------------------------------ 1.4 reference architectures

REFERENCE_ARCHITECTURES = ("augmented_llm", "rag_assistant", "fixed_workflow", "agentic_investigator",
                           "coordinator_specialists", "hitl_review_gate")


def reference_architecture(*, single_transformation: bool = False, answers_from_reference_docs: bool = False,
                           fixed_steps: bool = False, path_unknown: bool = False, parallel_specialists: bool = False,
                           checkpoint_before_action: bool = False) -> str:
    """Match a scenario to one of the six reference architectures.

    Check in this order (the most specific signal wins): checkpoint before an action takes effect
    -> hitl_review_gate; independent specialists -> coordinator_specialists; unknown path ->
    agentic_investigator; fixed steps -> fixed_workflow; answering from a large reference body ->
    rag_assistant; one transformation -> augmented_llm. Nothing matched -> ValueError.
    """
    if checkpoint_before_action:
        return "hitl_review_gate"
    if parallel_specialists:
        return "coordinator_specialists"
    if path_unknown:
        return "agentic_investigator"
    if fixed_steps:
        return "fixed_workflow"
    if answers_from_reference_docs:
        return "rag_assistant"
    if single_transformation:
        return "augmented_llm"
    raise ValueError("Describe the scenario: no signal given")
