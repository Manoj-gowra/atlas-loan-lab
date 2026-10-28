"""The ONE place the system talks to Claude: client, model routing, caching, cost.

LAB 2 exercises here:
  2.1 choose_model()   - route each task to its own tier (from design.TASK_DESIGN)
  2.4 build_system()   - stable content first with a cache breakpoint; variable content after it
  2.4 estimate_cost()  - what each call cost, including cache writes and reads
The rest is given: read call() to see how routing, cost and tracing happen once, for everyone.
"""
from __future__ import annotations

import time
from typing import Any

from . import config
from .design import TASK_DESIGN
from .prompting import compose
from .tracing import current_trace

_client: Any = None


def get_client() -> Any:
    """FakeClaude in fake mode, the real Anthropic SDK client in anthropic mode."""
    global _client
    if _client is None:
        if config.mode() == "anthropic":
            import anthropic  # pip install anthropic; needs ANTHROPIC_API_KEY in .env

            _client = anthropic.Anthropic()
            # Inside AWS (lesson 2.2): anthropic.AnthropicBedrock(aws_region="us-east-1") with the
            # Bedrock model IDs from your AWS console (they differ from the API IDs).
        else:
            from .fake_claude import FakeClaude

            _client = FakeClaude()
    return _client


def reset_client() -> None:
    global _client
    _client = None


def _read_prompt(name: str) -> str:
    return (config.PROMPTS / f"{name}.md").read_text()


def load_prompt(name: str) -> str:
    """Load prompts/<name>.md and resolve {{include: shared/...}} modules (prompting.compose)."""
    return compose(_read_prompt(name), _read_prompt)


# ------------------------------------------------------------------ LAB 2 TODOs


def choose_model(task: str) -> str:
    """API model ID for a task, from TASK_DESIGN and config.MODELS. ValueError for unknown tasks and
    for tasks a human does (model None)."""
    design = TASK_DESIGN.get(task)
    if design is None:
        raise ValueError(f"Unknown task {task!r}")
    if design.model is None:
        raise ValueError(f"Task {task!r} is done by a person; no model may be called for it")
    return config.MODELS[design.model]


def build_system(stable: str, dynamic: str | None = None) -> list[dict]:
    """A cache-friendly `system` parameter: [stable block WITH {"cache_control": {"type": "ephemeral"}},
    then the dynamic block (if any) WITHOUT cache_control]. Anything that changes per call - a
    timestamp, a request id, an applicant's name - must never be inside or before the stable block."""
    blocks = [{"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}}]
    if dynamic:
        blocks.append({"type": "text", "text": dynamic})
    return blocks


def estimate_cost(model: str, usage: Any) -> float:
    """USD for one response. Uncached input x input price; cache writes x input price x
    config.CACHE_WRITE_MULT; cache reads x input price x PRICES[model]["cache_read_mult"]; output x
    output price; all per million tokens. The real SDK may give None for cache fields: treat as 0."""
    price = config.PRICES[model]
    inp = (getattr(usage, "input_tokens", 0) or 0) * price["input"]
    write = (getattr(usage, "cache_creation_input_tokens", 0) or 0) * price["input"] * config.CACHE_WRITE_MULT
    read = (getattr(usage, "cache_read_input_tokens", 0) or 0) * price["input"] * price["cache_read_mult"]
    out = (getattr(usage, "output_tokens", 0) or 0) * price["output"]
    return round((inp + write + read + out) / 1_000_000, 8)


# ------------------------------------------------------------------ given


def call(task: str, messages: list[dict], system: Any = None, tools: list[dict] | None = None,
         tool_choice: dict | None = None, max_tokens: int = 1024, model: str | None = None) -> Any:
    """Call Claude for a task; routing, cost and tracing happen here. `model` overrides routing (A/B tests)."""
    model = model or choose_model(task)
    kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice
    start = time.perf_counter()
    response = get_client().messages.create(**kwargs)
    latency = getattr(response, "fake_latency_s", None) or (time.perf_counter() - start)
    trace = current_trace()
    if trace is not None:
        trace.add_llm_call(task, model, response.usage, estimate_cost(model, response.usage), latency, response.stop_reason)
    return response


def blocks_to_params(content: list) -> list[dict]:
    """Response content blocks -> plain dicts you can send back in `messages`."""
    out = []
    for b in content:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def text_of(response: Any) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def tool_uses(response: Any) -> list:
    return [b for b in response.content if b.type == "tool_use"]
