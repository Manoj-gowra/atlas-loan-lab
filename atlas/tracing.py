"""Structured tracing: one Trace per application; a Span per model call, tool call, retrieval or step.

GIVEN FILE - you USE it from Lab 3 on (3.6 Observability) and read traces in Lab 4.

What a trace for an LLM system must capture (3.6): model tier, cache hit/miss, which chunks
retrieval returned, which tools ran in what order, tokens, cost and latency - not just "it ran".
Spans written under `tagged(group=..., member=...)` belong to parallel work (the coordinator's
specialists), so the case latency counts the slowest member, not the sum.
"""
from __future__ import annotations

import contextvars
import json
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterator

from . import config


@dataclass
class Span:
    name: str
    kind: str  # "llm" | "tool" | "retrieval" | "step"
    latency_s: float = 0.0
    attrs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


_tags: contextvars.ContextVar[dict] = contextvars.ContextVar("atlas_span_tags", default={})


@contextmanager
def tagged(**tags: Any) -> Iterator[None]:
    """Tag every span recorded inside this block, e.g. tagged(group="investigation", member="industry_risk")."""
    token = _tags.set({**_tags.get(), **tags})
    try:
        yield
    finally:
        _tags.reset(token)


@dataclass
class Trace:
    trace_id: str
    spans: list[Span] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def _add(self, span: Span) -> None:
        span.attrs = {**_tags.get(), **span.attrs}
        with self._lock:
            self.spans.append(span)

    @contextmanager
    def span(self, name: str, kind: str = "step", **attrs: Any) -> Iterator[Span]:
        s = Span(name=name, kind=kind, attrs=dict(attrs))
        start = time.perf_counter()
        try:
            yield s
        except Exception as exc:
            s.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            s.latency_s = round(s.latency_s + time.perf_counter() - start, 4)
            self._add(s)

    def add_llm_call(self, task: str, model: str, usage: Any, cost_usd: float, latency_s: float,
                     stop_reason: str) -> None:
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self._add(Span(name=f"llm:{task}", kind="llm", latency_s=round(latency_s, 4), attrs={
            "task": task, "model": model, "cost_usd": cost_usd, "stop_reason": stop_reason,
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": cache_write,
            "cache": "hit" if cache_read else "write" if cache_write else "none",
        }))

    def add_retrieval(self, query: str, chunk_ids: list[str], **attrs: Any) -> None:
        self._add(Span(name="retrieval", kind="retrieval", attrs={"query": query, "chunk_ids": list(chunk_ids), **attrs}))

    # ---- roll-ups
    @property
    def cost_usd(self) -> float:
        return round(sum(s.attrs.get("cost_usd", 0.0) for s in self.spans if s.kind == "llm"), 6)

    @property
    def latency_s(self) -> float:
        """Sequential spans add up; a parallel group counts only its slowest member."""
        timed = [s for s in self.spans if s.kind in ("llm", "tool", "retrieval")]
        total = sum(s.latency_s for s in timed if "group" not in s.attrs)
        groups: dict[str, dict[str, float]] = {}
        for s in timed:
            if "group" in s.attrs:
                members = groups.setdefault(s.attrs["group"], {})
                key = s.attrs.get("member", "_")
                members[key] = members.get(key, 0.0) + s.latency_s
        total += sum(max(m.values()) for m in groups.values() if m)
        return round(total, 3)

    def llm_calls(self, task: str | None = None) -> list[Span]:
        return [s for s in self.spans if s.kind == "llm" and (task is None or s.attrs.get("task") == task)]

    def tool_calls(self) -> list[Span]:
        return [s for s in self.spans if s.kind == "tool"]

    def retrievals(self) -> list[Span]:
        return [s for s in self.spans if s.kind == "retrieval"]

    def save(self, redact: Callable[[str], str] | None = None) -> str:
        folder = config.RUNS / "traces"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.trace_id}.jsonl"
        with open(path, "w") as f:
            for s in self.spans:
                line = json.dumps(asdict(s), default=str)
                f.write((redact(line) if redact else line) + "\n")
        return str(path)


_current: contextvars.ContextVar[Trace | None] = contextvars.ContextVar("atlas_trace", default=None)


@contextmanager
def start_trace(trace_id: str) -> Iterator[Trace]:
    trace = Trace(trace_id=trace_id)
    token = _current.set(trace)
    try:
        yield trace
    finally:
        _current.reset(token)


def current_trace() -> Trace | None:
    return _current.get()


def load_trace(path: Any) -> list[dict]:
    """Read a saved trace file back as a list of span dicts."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
