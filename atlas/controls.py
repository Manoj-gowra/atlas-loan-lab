"""Exercise 1.0 - "What This Exam Tests": the exam's favourite distractors, as code.

Course lesson: What This Exam Tests. The sample question: a support agent that only needs to read
tickets and draft replies also holds refund and delete tools. Which change BEST reduces risk?
  - remove the tools            -> PREVENTIVE control (removes the risk at the root)   <- the answer
  - log every use               -> DETECTIVE control (tells you after it happened)
  - add a confirmation prompt   -> COMPENSATING control (capability still wired up)
  - use a bigger model          -> NOT A CONTROL (confuses instruction-following with authorization)

Writing the classifier yourself is how the reflex sticks.
"""

from __future__ import annotations

PREVENTIVE_WORDS = (
    "remove",
    "revoke",
    "scope",
    "read-only",
    "least privilege",
    "restrict",
    "disable",
    "split",
    "private",
)
DETECTIVE_WORDS = ("log", "audit", "monitor", "alert", "dashboard", "review later")
COMPENSATING_WORDS = (
    "confirm",
    "confirmation",
    "approval step",
    "second reviewer",
    "rate limit",
    "warning",
    "prompt instruction",
)
NOT_A_CONTROL_WORDS = (
    "bigger model",
    "larger model",
    "more capable model",
    "better model",
    "context window",
)


def classify_control(option: str) -> str:
    """Return "not_a_control", "preventive", "detective" or "compensating" for an answer option.

    Check NOT_A_CONTROL_WORDS first, then PREVENTIVE, DETECTIVE, COMPENSATING (case-insensitive,
    substring match). If nothing matches return "unknown".
    """
    # TODO (Lab 1): Lower-case the option and test the word lists in the order given in the docstring.
    text = option.lower()
    print(text)
    for label, words in (
        ("not_a_control", NOT_A_CONTROL_WORDS),
        ("preventive", PREVENTIVE_WORDS),
        ("detective", DETECTIVE_WORDS),
        ("compensating", COMPENSATING_WORDS),
    ):
        if any(word in text for word in words):
            return label
    return "unknown"


def best_risk_reduction(options: list[str]) -> str:
    """The option the exam wants when the goal is to REDUCE risk: the first preventive control.
    Raise ValueError if no option is preventive."""
    # TODO (Lab 1): Return the first option whose classify_control(...) is "preventive".
    for option in options:
        if classify_control(option) == "preventive":
            return option
    raise ValueError("No preventive option found")
