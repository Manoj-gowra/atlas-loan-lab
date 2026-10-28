"""LAB 2 - Exercise 2.3: intake as an AUGMENTED LLM (one bounded call) with structured output.

    forced tool call -> validate in code -> on error send SPECIFIC feedback and retry
                     -> still failing? stop and hand the case to a person (never guess)

Why forced? tool_choice={"type": "tool", "name": ...} makes Claude answer with arguments shaped by
your JSON schema instead of prose with JSON somewhere inside.
Why specific feedback? (lesson 4.2) "Extract more accurately" gives the model nothing new; naming
the field, the value it sent and what is required gives it a correction target.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from . import llm
from .schemas import ExtractedApplication, LoanApplication

TOOL_NAME = "record_application"


class ExtractionFailed(Exception):
    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


@dataclass
class ExtractionResult:
    application: LoanApplication
    confidence: dict[str, float]
    attempts: int
    errors: list[str] = field(default_factory=list)


def build_messages(doc_text: str) -> list[dict]:
    """Given. The per-request document goes in the USER message, wrapped so it reads as data."""
    return [{"role": "user", "content": (
        f"<document>\n{doc_text}\n</document>\n\n"
        f"Extract the application fields from the document above and record them with the {TOOL_NAME} tool.")}]


def application_tool() -> dict:
    """{"name": TOOL_NAME, "description": ..., "input_schema": ExtractedApplication.model_json_schema()}"""
    # TODO (Lab 2): Return the tool definition dict.
    raise NotImplementedError("Lab 2: implement application_tool()")


def validation_feedback(exc: ValidationError) -> str:
    """Specific feedback for a retry. One line per error:
        "- <field>: got <input value as repr> - <pydantic msg>"
    then a final line: "Fix only these fields and call record_application again. Money is a plain number in USD."
    (exc.errors() gives dicts with "loc", "input" and "msg".)"""
    # TODO (Lab 2): Loop over exc.errors(); field = ".".join of loc parts.
    raise NotImplementedError("Lab 2: implement validation_feedback()")


def extract(doc_text: str, prompt_name: str = "intake_v2", model: str | None = None,
            max_attempts: int = 3) -> ExtractionResult:
    """The validate-and-retry loop.
      system = llm.build_system(llm.load_prompt(prompt_name))     # stable -> cached
      response = llm.call("intake", messages, system=..., tools=[application_tool()],
                          tool_choice={"type": "tool", "name": TOOL_NAME}, max_tokens=1500, model=model)
      stop_reason "max_tokens" -> record an error and try again (never parse truncated output)
      ExtractedApplication.model_validate(tool_use.input); on ValidationError append the assistant
      turn (llm.blocks_to_params) and a user turn holding a tool_result for the same tool_use_id
      with "is_error": True and validation_feedback(exc) as content; then retry
      success -> ExtractionResult(LoanApplication without confidence, confidence, attempt, errors)
      out of attempts -> raise ExtractionFailed(message, errors)
    """
    # TODO (Lab 2): Implement the loop described above.
    raise NotImplementedError("Lab 2: implement extract()")
