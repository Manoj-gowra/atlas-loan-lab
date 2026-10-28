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
    return {"name": TOOL_NAME,
            "description": "Record the fields extracted from ONE commercial loan application package, with a "
                           "confidence score for each field.",
            "input_schema": ExtractedApplication.model_json_schema()}


def validation_feedback(exc: ValidationError) -> str:
    """Specific feedback for a retry. One line per error:
        "- <field>: got <input value as repr> - <pydantic msg>"
    then a final line: "Fix only these fields and call record_application again. Money is a plain number in USD."
    (exc.errors() gives dicts with "loc", "input" and "msg".)"""
    lines = [f"- {'.'.join(str(p) for p in e['loc'])}: got {e.get('input')!r} - {e['msg']}" for e in exc.errors()]
    lines.append(f"Fix only these fields and call {TOOL_NAME} again. Money is a plain number in USD.")
    return "\n".join(lines)


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
    system = llm.build_system(llm.load_prompt(prompt_name))
    messages = build_messages(doc_text)
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        response = llm.call("intake", messages, system=system, tools=[application_tool()],
                            tool_choice={"type": "tool", "name": TOOL_NAME}, max_tokens=1500, model=model)
        if response.stop_reason == "max_tokens":
            errors.append(f"attempt {attempt}: output truncated (max_tokens)")
            continue
        uses = [b for b in llm.tool_uses(response) if b.name == TOOL_NAME]
        if not uses:
            errors.append(f"attempt {attempt}: no {TOOL_NAME} call")
            continue
        try:
            data = ExtractedApplication.model_validate(uses[0].input)
        except ValidationError as exc:
            errors.append(f"attempt {attempt}: {exc}")
            messages = messages + [
                {"role": "assistant", "content": llm.blocks_to_params(response.content)},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": uses[0].id, "is_error": True,
                                              "content": validation_feedback(exc)}]},
            ]
            continue
        app = LoanApplication.model_validate(data.model_dump(exclude={"confidence"}))
        return ExtractionResult(app, data.confidence, attempt, errors)
    raise ExtractionFailed(f"No valid extraction after {max_attempts} attempts", errors)
