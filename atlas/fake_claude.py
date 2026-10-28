"""FakeClaude: an offline, deterministic stand-in for the Claude Messages API.

GIVEN FILE - don't edit it, but DO read this docstring once. It is your "model" until you have an
API key. It takes the same arguments as `anthropic.Anthropic().messages.create(...)` and returns
objects with the same attribute names (`.content`, `.stop_reason`, `.usage`). Switch to real
Claude with ATLAS_MODE=anthropic; your code does not change.

It plays seven scripted roles, chosen from the tools and tags in each request:
intake extractor, policy explainer, memo writer, the three investigation specialists from course
lesson 1.3 (financial-ratio, business-history, industry-risk) and an LLM judge (lesson 4.1).

Realistic failure modes it simulates ON PURPOSE (your code must handle them):
 1. API validation: unknown model -> 404; every `tool_use` must get a `tool_result` in the next
    user message -> 400, same rule as the real API.
 2. Without a forced `tool_choice`, extraction comes back as chatty prose with JSON inside.
 3. On the FIRST extraction attempt some documents return "180k" for a number -> validation error.
 4. Haiku misreads free-form documents (loan term vs lease term, debts to sum, monthly/quarterly
    figures) unless the prompt has at least two worked <example>...</example> blocks - and it is
    CONFIDENT when wrong.
 5. Some fields come back with confidence below 0.8.
 6. The explainer invents one citation on its first attempt; it stops when your feedback NAMES it.
 7. Indirect prompt injection: if a document's injected instruction reaches it, extraction and
    the memo writer obey.
 8. Given a date of birth or age, the memo writer mentions age (a prohibited factor).
 9. Specialists call tools in parallel, retry a timed-out tool once, try to look up a record
    outside the case (an affiliate), report an out-of-scope aside, and one gets stuck in a loop.
10. Specialists only recompute ratios if their brief contains the figures they need.
11. Token usage is estimated (~4 characters per token); a repeated prefix marked with
    cache_control reports cache_creation then cache_read tokens (5-minute TTL).
12. Each response carries `fake_latency_s`, a simulated duration by model and size.

It has an answer key for the sample documents (data/.fake/answer_key.json). Real Claude reads
the text instead, so real results vary a little.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import config

# ---------------------------------------------------------------- response objects (SDK-shaped)


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class Message:
    id: str
    model: str
    content: list
    stop_reason: str
    usage: Usage
    role: str = "assistant"
    type: str = "message"
    fake_latency_s: float = 0.0


class FakeAPIError(Exception):
    """Raised for requests the real API would reject (same status codes)."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Error code: {status_code} - {message}")
        self.status_code = status_code
        self.message = message


# ---------------------------------------------------------------- helpers

INJECTION_RE = re.compile(r"ignore (all )?(previous|prior) instructions", re.I)
SPEED = {"claude-haiku-5-5": (0.35, 220.0), "claude-sonnet-5-5": (0.8, 110.0), "claude-opus-5-5": (1.4, 70.0)}
HALLUCINATED_ID = "POL-GEN-v1-4.2"
SPECIALIST_TOOLS = {"get_verified_financials": "financial_ratio", "get_public_filings": "business_history",
                    "get_industry_risk": "industry_risk"}


def _get(block: Any, key: str, default: Any = None) -> Any:
    return block.get(key, default) if isinstance(block, dict) else getattr(block, key, default)


def _tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _block_text(block: Any) -> str:
    if isinstance(block, str):
        return block
    kind = _get(block, "type")
    if kind == "text":
        return _get(block, "text", "")
    if kind == "tool_use":
        return json.dumps(_get(block, "input", {}))
    if kind == "tool_result":
        inner = _get(block, "content", "")
        return "\n".join(_block_text(b) for b in inner) if isinstance(inner, list) else str(inner)
    return ""


def _content_blocks(content: Any) -> list:
    return [{"type": "text", "text": content}] if isinstance(content, str) else list(content or [])


def _message_text(msg: dict) -> str:
    return "\n".join(_block_text(b) for b in _content_blocks(msg.get("content")))


def _system_blocks(system: Any) -> list:
    if system is None:
        return []
    return [{"type": "text", "text": system}] if isinstance(system, str) else list(system)


def _load_answer_key() -> dict:
    path = config.DATA / ".fake" / "answer_key.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _money(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"\$?([\d,]+(?:\.\d+)?)", text)
    return float(m.group(1).replace(",", "")) if m else None


# ---------------------------------------------------------------- the client


class FakeClaude:
    """Drop-in for anthropic.Anthropic(): use `client.messages.create(...)`."""

    def __init__(self) -> None:
        self.messages = _Messages(self)
        self.calls: list[dict] = []  # every request, so tests can see what was SENT to the model
        self._cache: dict[str, float] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self._answer_key = _load_answer_key()

    def next_id(self, prefix: str) -> str:
        with self._lock:
            self._counter += 1
            return f"{prefix}_fake_{self._counter:05d}"

    def sent_text(self) -> str:
        """Everything this client has sent to the 'model' (for privacy tests)."""
        return "\n".join(c["all_text"] for c in self.calls)


class _Messages:
    def __init__(self, client: FakeClaude) -> None:
        self.client = client

    def create(self, *, model: str, max_tokens: int, messages: list, system: Any = None,
               tools: list | None = None, tool_choice: dict | None = None,
               temperature: float | None = None, metadata: dict | None = None,
               stop_sequences: list | None = None, **_: Any) -> Message:
        _validate(model, max_tokens, messages, tools, tool_choice)
        system_list = _system_blocks(system)
        all_text = "\n".join([_block_text(b) for b in system_list] + [_message_text(m) for m in messages])
        tool_names = [t["name"] for t in (tools or [])]
        with self.client._lock:
            self.client.calls.append({"model": model, "tools": tool_names, "all_text": all_text,
                                      "system_text": "\n".join(_block_text(b) for b in system_list),
                                      "n_messages": len(messages), "tool_choice": tool_choice})
        ctx = _Ctx(client=self.client, model=model, messages=messages, all_text=all_text,
                   tool_names=tool_names, tool_choice=tool_choice or {})
        user = ctx.user_text()
        if "record_application" in tool_names:
            content, stop = _extraction(ctx)
        elif "record_judgment" in tool_names:
            content, stop = _judge(ctx)
        elif "submit_findings" in tool_names:
            role = next((r for t, r in SPECIALIST_TOOLS.items() if t in tool_names), "generalist")
            content, stop = _specialist(ctx, role)
        elif "<policy_chunk" in user:
            content, stop = _explainer(ctx)
        elif "<case_summary>" in user:
            content, stop = _memo(ctx)
        else:
            content, stop = [TextBlock(
                "[fake mode] I'm the offline stand-in for Claude, so I only play the scripted roles in this "
                "project. Set ATLAS_MODE=anthropic to talk to real Claude.")], "end_turn"

        out_text = "".join(_block_text(b) for b in content)
        output_tokens = _tokens(out_text) + 8
        if output_tokens > max_tokens:  # truncated, exactly like the real API
            content, stop, output_tokens = [TextBlock(out_text[: max_tokens * 4])], "max_tokens", max_tokens
        usage = _usage(self.client, model, tools, system_list, messages, output_tokens)
        base, speed = SPEED[model]
        latency = round(base + output_tokens / speed + usage.input_tokens / 40000, 3)
        return Message(id=self.client.next_id("msg"), model=model, content=content, stop_reason=stop,
                       usage=usage, fake_latency_s=latency)


@dataclass
class _Ctx:
    client: FakeClaude
    model: str
    messages: list
    all_text: str
    tool_names: list
    tool_choice: dict
    extra: dict = field(default_factory=dict)

    def user_text(self) -> str:
        return "\n".join(_message_text(m) for m in self.messages if m.get("role") == "user")

    def use(self, name: str, args: dict) -> ToolUseBlock:
        return ToolUseBlock(id=self.client.next_id("toolu"), name=name, input=args)


# ---------------------------------------------------------------- validation (mirrors real 400s)


def _validate(model: str, max_tokens: int, messages: list, tools: list | None, tool_choice: dict | None) -> None:
    if model not in config.PRICES:
        raise FakeAPIError(404, f"model: {model} not found. Use an ID from config.MODELS.")
    if not isinstance(max_tokens, int) or max_tokens < 1:
        raise FakeAPIError(400, "max_tokens: must be a positive integer")
    if not messages:
        raise FakeAPIError(400, "messages: at least one message is required")
    if messages[0].get("role") != "user":
        raise FakeAPIError(400, "messages.0.role: the first message must use the 'user' role")
    for t in tools or []:
        if "name" not in t or "input_schema" not in t:
            raise FakeAPIError(400, "tools: every tool needs a 'name' and an 'input_schema'")
    names = {t["name"] for t in tools or []}
    if tool_choice and tool_choice.get("type") == "tool" and tool_choice.get("name") not in names:
        raise FakeAPIError(400, f"tool_choice: tool '{tool_choice.get('name')}' is not in tools")
    for i, msg in enumerate(messages):
        if msg.get("role") not in ("user", "assistant"):
            raise FakeAPIError(400, f"messages.{i}.role: must be 'user' or 'assistant'")
        blocks = _content_blocks(msg.get("content"))
        if msg["role"] == "assistant":
            ids = [_get(b, "id") for b in blocks if _get(b, "type") == "tool_use"]
            if ids and i + 1 < len(messages):
                nxt = messages[i + 1]
                answered = {_get(b, "tool_use_id") for b in _content_blocks(nxt.get("content"))
                            if _get(b, "type") == "tool_result"}
                missing = [x for x in ids if x not in answered]
                if nxt.get("role") != "user" or missing:
                    raise FakeAPIError(400, (
                        f"messages.{i + 1}: `tool_use` ids were found without `tool_result` blocks immediately "
                        f"after: {', '.join(missing or ids)}. Each `tool_use` block must have a corresponding "
                        "`tool_result` block in the next message."))
        else:
            results = [_get(b, "tool_use_id") for b in blocks if _get(b, "type") == "tool_result"]
            if results:
                prev = messages[i - 1] if i > 0 else {}
                prev_ids = {_get(b, "id") for b in _content_blocks(prev.get("content")) if _get(b, "type") == "tool_use"}
                unexpected = [r for r in results if r not in prev_ids]
                if unexpected:
                    raise FakeAPIError(400, f"messages.{i}: unexpected `tool_use_id` found in `tool_result` blocks: "
                                            f"{', '.join(unexpected)}")


# ---------------------------------------------------------------- usage + prompt caching


def _usage(client: FakeClaude, model: str, tools: list | None, system_list: list, messages: list,
           output_tokens: int) -> Usage:
    segments: list[tuple[str, bool]] = []
    for t in tools or []:
        segments.append((json.dumps(t, sort_keys=True), bool(t.get("cache_control"))))
    for b in system_list:
        segments.append((_block_text(b), bool(_get(b, "cache_control"))))
    for m in messages:
        for b in _content_blocks(m.get("content")):
            segments.append((_block_text(b), bool(_get(b, "cache_control"))))
    total = sum(_tokens(s) for s, _ in segments) + 4 * len(messages)
    breakpoints = [i for i, (_, cc) in enumerate(segments) if cc]
    if not breakpoints:
        return Usage(input_tokens=total, output_tokens=output_tokens)
    prefix = segments[: breakpoints[-1] + 1]
    prefix_tokens = sum(_tokens(s) for s, _ in prefix)
    if prefix_tokens < config.MIN_CACHEABLE_TOKENS:
        return Usage(input_tokens=total, output_tokens=output_tokens)  # too short: silently not cached
    key = hashlib.sha256((model + "".join(s for s, _ in prefix)).encode()).hexdigest()
    now = time.time()
    with client._lock:
        hit = key in client._cache and now - client._cache[key] < 300
        client._cache[key] = now
    if hit:
        return Usage(input_tokens=total - prefix_tokens, output_tokens=output_tokens, cache_read_input_tokens=prefix_tokens)
    return Usage(input_tokens=total - prefix_tokens, output_tokens=output_tokens, cache_creation_input_tokens=prefix_tokens)


# ---------------------------------------------------------------- role: intake extraction


def _regex_extract(text: str) -> dict:
    """Best-effort fallback for documents not in the answer key."""
    def find(pattern: str, default: Any = None) -> Any:
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else default

    product = (find(r"product:\s*([^\n]+)", "") or "").lower()
    loan_type = ("ag_equipment" if "agricultural" in product else "equipment" if "equipment" in product
                 else "cre" if "real estate" in product else "term")
    return {
        "application_id": find(r"(APP-\d{3})", "APP-000"),
        "business_name": find(r"(?:business legal name|company|business):\s*([^\n]+)", "unknown"),
        "customer_id": find(r"(B-\d{4})", "B-0000"),
        "loan_type": loan_type,
        "jurisdiction": find(r"(US-[A-Z]{2})", "US-CA"),
        "amount_requested": _money(find(r"amount requested:\s*([^\n]+)")) or 0,
        "term_months": int(_money(find(r"term:\s*([^\n]+)")) or 60),
        "annual_revenue": _money(find(r"annual revenue:\s*([^\n]+)")) or 0,
        "ebitda": _money(find(r"ebitda:\s*([^\n]+)")) or 0,
        "existing_annual_debt_service": _money(find(r"existing annual debt service:\s*([^\n]+)")) or 0,
        "collateral_value": _money(find(r"appraised at\s*([^\n]+)")) or 0,
        "years_in_business": float(_money(find(r"years in business:\s*([^\n]+)")) or 0),
        "purpose": find(r"purpose:\s*([^\n]+)", "unspecified"),
        "submitted_on": find(r"submitted:\s*(\d{4}-\d{2}-\d{2})", "2026-01-01"),
    }


def _extraction(ctx: _Ctx) -> tuple[list, str]:
    text = ctx.user_text()
    match = re.search(r"APP-\d{3}", text)
    key = ctx.client._answer_key.get(match.group(0)) if match else None
    is_retry = any(_get(b, "type") == "tool_use" and _get(b, "name") == "record_application"
                   for m in ctx.messages if m.get("role") == "assistant" for b in _content_blocks(m.get("content")))
    if key is None:
        fields, confidence = _regex_extract(text), {}
    else:
        fields, confidence = dict(key["fields"]), dict(key.get("confidence", {}))
        examples = len(re.findall(r"<example>.*?</example>", ctx.all_text, re.S))
        if "haiku" in ctx.model and examples < 2:
            for name, wrong in key.get("small_model_zero_shot", {}).items():
                fields[name], confidence[name] = wrong, 0.9  # confidently wrong
        if key.get("injected") and INJECTION_RE.search(text):  # injected text in the DOCUMENT reached the model
            fields.update(key["injected"])
        if not is_retry:
            fields.update(key.get("first_attempt", {}))
    confidence = {name: confidence.get(name, 0.95) for name in fields if name != "application_id"}
    payload = {**fields, "confidence": confidence}
    forced = ctx.tool_choice.get("type") == "any" or (
        ctx.tool_choice.get("type") == "tool" and ctx.tool_choice.get("name") == "record_application")
    if not forced:
        return [TextBlock("Sure! Here's what I extracted:\n\n```json\n" + json.dumps(payload, indent=2)
                          + "\n```\n\nLet me know if you'd like me to double-check anything!")], "end_turn"
    return [ctx.use("record_application", payload)], "tool_use"


# ---------------------------------------------------------------- role: policy explainer

RULE_WORDS = {"credit_score": "credit score", "dscr": "DSCR", "ltv": "LTV", "loan_amount": "loan amount",
              "time_in_business": "time in business"}


def _rule_results(text: str) -> list[dict]:
    m = re.search(r"<rule_results[^>]*>(.*?)</rule_results>", text, re.S)
    try:
        rows = json.loads(m.group(1)) if m else []
    except json.JSONDecodeError:
        rows = []
    return [r for r in rows if isinstance(r, dict)]


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.])\s", text, maxsplit=1)[0] if text else ""


def _explainer(ctx: _Ctx) -> tuple[list, str]:
    text = ctx.user_text()
    chunks = re.findall(r'<policy_chunk\s+id="([^"]+)"(?:\s+\w+="[^"]*")*\s*>(.*?)</policy_chunk>', text, re.S)
    chunk_text = {cid: re.sub(r"^\d+\.\d+[^\n]*\n", "", body.strip()).strip() for cid, body in chunks}
    rules = _rule_results(text)
    flagged = [r for r in rules if r.get("status") != "pass"]
    lines = ["Explanation for the credit officer:", ""]
    used: set[str] = set()
    for r in flagged:
        # cite the retrieved chunk for this rule's section, whatever version retrieval returned
        sec = str(r.get("policy_ref", "")).rsplit("-", 1)[-1]
        pol = str(r.get("policy_ref", "")).split("-v")[0]
        cid = next((c for c in chunk_text if c.startswith(pol + "-v") and c.endswith("-" + sec)), None)
        cite = f" [{cid}]" if cid else ""
        lines.append(f"- {RULE_WORDS.get(r.get('rule_id'), r.get('rule_id'))} is {r.get('status')}: {r.get('detail', '')}.{cite}")
        if cid:
            used.add(cid)
            lines.append(f"  Policy: {_first_sentence(chunk_text[cid])}")
    for cid, body in list(chunk_text.items())[:4]:
        if cid not in used:
            lines.append(f"- {_first_sentence(body)} [{cid}]")
    if any(r.get("rule_id") in ("dscr", "credit_score") for r in flagged):
        lines.append("- Next: review verified financials and bank activity before deciding.")
    if len(chunks) >= 2 and HALLUCINATED_ID not in text:
        lines.append(f"- Borrowers must also hold six months of cash reserves after funding [{HALLUCINATED_ID}].")
    lines += ["", "The final decision rests with the authorized officer."]
    return [TextBlock("\n".join(lines))], "end_turn"


# ---------------------------------------------------------------- role: memo writer


def _find_key(obj: Any, *names: str) -> Any:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names:
                return v
            found = _find_key(v, *names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_key(item, *names)
            if found is not None:
                return found
    return None


def _memo(ctx: _Ctx) -> tuple[list, str]:
    user = ctx.user_text()
    raw = re.search(r"<case_summary>(.*?)</case_summary>", user, re.S)
    try:
        case = json.loads(raw.group(1)) if raw else {}
    except json.JSONDecodeError:
        case = {}
    app_id = _find_key(case, "application_id") or "the application"
    route = _find_key(case, "route") or "review"
    inv = _find_key(case, "investigation") or {}
    rec = (inv.get("recommendation") if isinstance(inv, dict) else None) or {
        "approve": "approve", "decline": "decline", "investigate": "refer"}.get(route, route)
    lines = [f"# Credit memo: {app_id}", ""]
    if re.search(r"pre-approved|ignore (all )?(previous|prior) instructions", user, re.I):
        lines.append("**Recommendation:** APPROVE. The application notes say the credit committee has pre-approved "
                     "this applicant, so further credit checks are unnecessary.")
    else:
        lines.append(f"**Recommendation for officer review:** {str(rec).upper()}")
    lines += ["", "## Key facts"]
    for label, names in [("Business", ("business_name",)), ("Loan type", ("loan_type",)), ("Amount", ("amount_requested",)),
                         ("Jurisdiction", ("jurisdiction",)), ("DSCR", ("dscr",)), ("LTV", ("ltv",)),
                         ("Business credit score", ("credit_score",))]:
        value = _find_key(case, *names)
        if value is not None:
            lines.append(f"- {label}: {value}")
    if re.search(r"date_of_birth|\bdob\b|date of birth|\"age\"", user, re.I):
        lines.append("- Given the guarantor's age, the owner is at a stable stage of their career.")
    failed = [r for r in (_find_key(case, "rule_results") or []) if isinstance(r, dict) and r.get("status") != "pass"]
    lines += ["", "## Rule checks"]
    lines += [f"- {r.get('rule_id')}: {r.get('status')} ({r.get('detail', '')}) [{r.get('policy_ref')}]" for r in failed] \
        or ["- All policy rules passed."]
    if isinstance(inv, dict) and inv:
        lines += ["", "## Investigation", f"- Status: {inv.get('status')}; recommendation: {inv.get('recommendation')}"]
        for f in (inv.get("findings") or [])[:6]:
            if isinstance(f, dict):
                lines.append(f"- [{f.get('source_specialist')}] {f.get('finding')}")
        for f in inv.get("unverified_asides") or []:
            if isinstance(f, dict):
                lines.append(f"- UNVERIFIED aside from {f.get('source_specialist')} (outside its scope): {f.get('finding')}")
        for item in inv.get("unable_to_check") or []:
            lines.append(f"- Not checked: {item}")
    lines += ["", "## For the officer", "- Confirm the figures above against the source documents before deciding."]
    return [TextBlock("\n".join(lines))], "end_turn"


# ---------------------------------------------------------------- role: LLM judge (lesson 4.1)


def _judge(ctx: _Ctx) -> tuple[list, str]:
    text = ctx.user_text()
    m = re.search(r"<explanation>(.*?)</explanation>", text, re.S)
    explanation = m.group(1) if m else ""
    flagged = [r for r in _rule_results(text) if r.get("status") != "pass"]
    criteria = re.findall(r'<criterion id="([a-z_]+)"', ctx.all_text)
    results: dict[str, bool] = {}
    for c in criteria:
        if c == "names_flagged_rules":
            results[c] = all(RULE_WORDS.get(r.get("rule_id"), "").lower() in explanation.lower() for r in flagged)
        elif c == "cites_flagged_sections":
            results[c] = all(str(r.get("policy_ref")) in explanation for r in flagged)
        elif c == "no_decision_language":
            results[c] = not re.search(r"I recommend|should be (approved|declined)|recommend (approval|declin)", explanation, re.I)
        elif c == "gives_next_step":
            results[c] = "next:" in explanation.lower() or not flagged
        else:
            results[c] = True  # the fake can't judge criteria it doesn't know; real Claude can
    verdict = {"criteria": results, "passed": all(results.values()) if results else False,
               "notes": "Judged only against the listed criteria."}
    return [ctx.use("record_judgment", verdict)], "tool_use"


# ---------------------------------------------------------------- roles: investigation specialists (lesson 1.3)


def _history(messages: list) -> tuple[list, dict]:
    calls, results = [], {}
    for m in messages:
        for b in _content_blocks(m.get("content")):
            if m.get("role") == "assistant" and _get(b, "type") == "tool_use":
                calls.append({"id": _get(b, "id"), "name": _get(b, "name"), "input": _get(b, "input") or {}})
            if m.get("role") == "user" and _get(b, "type") == "tool_result":
                results[_get(b, "tool_use_id")] = (_block_text(b), bool(_get(b, "is_error")))
    return calls, results


def _parse(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _brief_value(brief: str, key: str) -> float | None:
    m = re.search(rf"^{key}:\s*([^\n]+)$", brief, re.I | re.M)
    return _money(m.group(1)) if m else None


def _specialist(ctx: _Ctx, role: str) -> tuple[list, str]:
    brief = _message_text(ctx.messages[0])
    app = re.search(r"APP-\d{3}", brief)
    cust = re.search(r"B-\d{4}", brief)
    app_id, customer = (app.group(0) if app else "APP-000"), (cust.group(0) if cust else "B-0000")
    calls, results = _history(ctx.messages)

    def ok(name: str) -> list:
        return [c for c in calls if c["name"] == name and c["id"] in results and not results[c["id"]][1]]

    def failed(name: str) -> list:
        return [c for c in calls if c["name"] == name and c["id"] in results and results[c["id"]][1]]

    def data(name: str) -> Any:
        hits = ok(name)
        return _parse(results[hits[-1]["id"]][0]) if hits else None

    def submit(findings: list, recommendation: str, metrics: dict | None = None) -> tuple[list, str]:
        payload = {"findings": findings, "recommendation": recommendation}
        if metrics:
            payload["metrics"] = metrics
        return [TextBlock("I have what I need for my scope."), ctx.use("submit_findings", payload)], "tool_use"

    if role == "financial_ratio":
        if not calls:
            return [TextBlock(f"Checking verified financials and 12 months of deposits for {customer}."),
                    ctx.use("get_verified_financials", {"customer_id": customer}),
                    ctx.use("get_bank_statements", {"customer_id": customer, "months": 12})], "tool_use"
        if not ok("get_bank_statements") and len(failed("get_bank_statements")) == 1:
            return [TextBlock("The bank service timed out; retrying once."),
                    ctx.use("get_bank_statements", {"customer_id": customer, "months": 12})], "tool_use"
        fin, bank = data("get_verified_financials"), data("get_bank_statements")
        findings, rec, metrics = [], "inconclusive", {}
        stated, total_ads, min_dscr = (_brief_value(brief, "stated EBITDA"), _brief_value(brief, "total annual debt service"),
                                       _brief_value(brief, "minimum DSCR"))
        if isinstance(fin, dict) and stated and total_ads and min_dscr:
            v = fin["verified_ebitda"]
            dscr = round(v / total_ads, 2)
            diff = (v - stated) / stated
            findings.append({"finding": f"Verified EBITDA ${v:,} vs stated ${stated:,.0f} ({diff:+.0%}); DSCR on verified "
                                        f"EBITDA is {dscr} against a {min_dscr} minimum", "in_scope": True,
                             "confidence": "high", "unable_to_check": None})
            rec = "support_approval" if dscr >= min_dscr else "support_decline"
            metrics = {"verified_ebitda": v, "stated_ebitda": stated, "verified_dscr": dscr}
        else:
            findings.append({"finding": "Could not recompute DSCR", "in_scope": True, "confidence": "low",
                             "unable_to_check": "DSCR recomputation (brief did not include stated EBITDA, total annual "
                                                "debt service and minimum DSCR)"})
        if isinstance(bank, dict):
            rows = bank.get("statements", [])
            nsf = sum(int(r.get("nsf_count", 0)) for r in rows[-6:])
            findings.append({"finding": f"{nsf} NSF events in the last 6 months", "in_scope": True,
                             "confidence": "high", "unable_to_check": None})
            if nsf >= 2:
                rec = "support_decline"
        else:
            findings.append({"finding": "Bank statements unavailable", "in_scope": True, "confidence": "low",
                             "unable_to_check": "bank statement review (service unavailable)"})
        if app_id == "APP-006":
            findings.append({"finding": "Bank memo lines show regular transfers to 'Herrera Electric Services LLC', "
                                        "possibly an affiliated business", "in_scope": False, "confidence": "low",
                             "unable_to_check": None})
        return submit(findings, rec, metrics)

    if role == "business_history":
        if not calls:
            return [TextBlock(f"Pulling the business credit report and public filings for {customer}."),
                    ctx.use("get_business_credit_report", {"customer_id": customer}),
                    ctx.use("get_public_filings", {"customer_id": customer, "years": 3})], "tool_use"
        if app_id == "APP-006" and not any(c["input"].get("customer_id") == "B-1012" for c in calls):
            return [TextBlock("The related company B-1012 may matter; checking its report too."),
                    ctx.use("get_business_credit_report", {"customer_id": "B-1012"})], "tool_use"
        if app_id == "APP-007":
            years = max(int(c["input"].get("years", 3)) for c in calls if c["name"] == "get_public_filings") + 2
            return [TextBlock("The 2025 judgment needs older context; widening the filings search."),
                    ctx.use("get_public_filings", {"customer_id": customer, "years": years})], "tool_use"
        report, filings = data("get_business_credit_report"), data("get_public_filings")
        findings, rec = [], "inconclusive"
        if isinstance(report, dict) and report.get("customer_id") == customer:
            findings.append({"finding": f"Business credit score {report['score']}, {report['days_beyond_terms']} days "
                                        f"beyond terms, {report['open_tax_liens']} open tax liens", "in_scope": True,
                             "confidence": "high", "unable_to_check": None})
            rec = "support_decline" if report["open_tax_liens"] or report["days_beyond_terms"] > 15 else "support_approval"
        else:
            findings.append({"finding": "Business credit report not reviewed", "in_scope": True, "confidence": "low",
                             "unable_to_check": "business credit report (not authorized or unavailable)"})
        if isinstance(filings, dict):
            open_items = [f for f in filings.get("filings", []) if f.get("status") == "open"]
            findings.append({"finding": f"{len(open_items)} open public filings (liens or judgments)", "in_scope": True,
                             "confidence": "high", "unable_to_check": None})
        else:
            findings.append({"finding": "Public filings not reviewed", "in_scope": True, "confidence": "low",
                             "unable_to_check": "public filings (not authorized or unavailable)"})
            rec = "inconclusive"
        if any(c["input"].get("customer_id") == "B-1012" for c in calls):
            findings.append({"finding": "Affiliate B-1012 not reviewed", "in_scope": True, "confidence": "medium",
                             "unable_to_check": "affiliate B-1012 is outside this case's authorized scope"})
        return submit(findings, rec)

    if role == "industry_risk":
        if not calls:
            return [TextBlock(f"Checking sector conditions for {customer}."),
                    ctx.use("get_industry_risk", {"customer_id": customer})], "tool_use"
        risk = data("get_industry_risk")
        if "search_policy" in ctx.tool_names and not ok("search_policy") and not failed("search_policy"):
            sector = risk.get("sector", "") if isinstance(risk, dict) else ""
            return [TextBlock("Checking what policy says for this sector."),
                    ctx.use("search_policy", {"query": f"{sector} debt service coverage seasonal deposits"})], "tool_use"
        if not isinstance(risk, dict):
            return submit([{"finding": "Industry data unavailable", "in_scope": True, "confidence": "low",
                            "unable_to_check": "industry risk"}], "inconclusive")
        s = risk.get("stress_index", 50)
        rec = "support_decline" if s >= 70 else "support_approval" if s < 50 else "inconclusive"
        return submit([{"finding": f"Sector '{risk.get('sector')}' stress index {s}/100 ({risk.get('outlook')}): "
                                   f"{risk.get('note')}", "in_scope": True, "confidence": "medium",
                        "unable_to_check": None}], rec)

    return submit([{"finding": "No specialist role recognised", "in_scope": False, "confidence": "low",
                    "unable_to_check": "everything"}], "inconclusive")
