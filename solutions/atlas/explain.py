"""LAB 3 - Exercise 3.3 (generate step) + 4.3/5.1 preview: grounded explanations with verified citations.

The last step of the policy-check WORKFLOW: Claude (Sonnet) explains the rule results using ONLY
retrieved policy chunks, citing chunk ids. Your code then checks every citation against the chunks
actually sent. An invented citation is a hallucination you can detect deterministically - so detect
it, give feedback that NAMES it, retry once, and if it persists strip it and flag the case.
(Telling the model "don't hallucinate" is guidance; this check is enforcement.)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import llm
from .rag import Chunk, PolicyIndex, format_chunks, retrieve
from .rules import RuleReport
from .schemas import LoanApplication
from .tracing import current_trace

CITATION_RE = re.compile(r"\[([A-Z]+-[A-Z]+-v\d+-\d+\.\d+)\]")
RULE_QUERIES = {
    "credit_score": "minimum business credit score bureau",
    "dscr": "debt service coverage ratio DSCR minimum",
    "ltv": "collateral coverage loan-to-value LTV maximum",
    "loan_amount": "loan amount limits range",
    "time_in_business": "time in business years operated",
}
STATE_NAMES = {"US-CA": "California", "US-NY": "New York", "US-TX": "Texas"}


@dataclass
class Explanation:
    text: str
    citations: list[str]
    attempts: int
    chunk_ids: list[str] = field(default_factory=list)
    removed_citations: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return bool(self.removed_citations)


def gather_chunks(app: LoanApplication, report: RuleReport, per_query: int = 2,
                  index: PolicyIndex | None = None) -> list[Chunk]:
    """Given. Retrieve for every rule that did not pass (or all rules if all passed) plus the
    jurisdiction rules; de-duplicated; each retrieval is recorded on the trace (3.6)."""
    rules = report.not_passed or report.results
    queries = [(RULE_QUERIES[r.rule_id], per_query) for r in rules]
    queries.append((f"jurisdiction rules {STATE_NAMES.get(app.jurisdiction, app.jurisdiction)}", 1))
    seen: dict[str, Chunk] = {}
    trace = current_trace()
    for query, k in queries:
        hits = retrieve(query, app.loan_type, app.jurisdiction, app.submitted_on, k=k, index=index)
        if trace is not None:
            trace.add_retrieval(query, [c.id for c in hits])
        for c in hits:
            seen.setdefault(c.id, c)
    return list(seen.values())


def find_citations(text: str) -> list[str]:
    """Given: citation ids in order of appearance, without duplicates."""
    return list(dict.fromkeys(CITATION_RE.findall(text)))


# ------------------------------------------------------------------ LAB 3 TODOs


def build_messages(app: LoanApplication, report: RuleReport, chunks: list[Chunk]) -> list[dict]:
    """ONE user message holding, in this order:
      <application_facts>JSON of app.model_dump(mode="json")</application_facts>
      <rule_results route="...">JSON list of each RuleResult's __dict__</rule_results>
      format_chunks(chunks)
      a final instruction to explain for the officer, citing only the provided chunk ids.
    (Per-request content goes in the USER message, never the system prompt - lesson 2.3.)"""
    facts = json.dumps(app.model_dump(mode="json"), indent=2)
    results = json.dumps([r.__dict__ for r in report.results], indent=2, default=str)
    content = (f"<application_facts>\n{facts}\n</application_facts>\n\n"
               f"<rule_results route=\"{report.route}\">\n{results}\n</rule_results>\n\n"
               f"{format_chunks(chunks)}\n\n"
               "Explain these results for the loan officer. Cite only the chunk ids provided above.")
    return [{"role": "user", "content": content}]


def invalid_citations(text: str, allowed_ids: set[str]) -> list[str]:
    """Citations in text that are not in allowed_ids, in order of appearance."""
    return [c for c in find_citations(text) if c not in allowed_ids]


def explain(app: LoanApplication, report: RuleReport, chunks: list[Chunk], max_attempts: int = 2) -> Explanation:
    """Generate -> verify -> feedback -> (strip and flag).
      system = llm.build_system(llm.load_prompt("explainer"))   (long and stable -> cached)
      llm.call("policy_check", messages, system=system, max_tokens=900)
      invalid citations -> append the assistant text and a user message NAMING the invalid ids, retry
      still invalid after max_attempts -> replace each "[ID]" with "[citation removed: not in retrieved
      policy]" and list them in removed_citations
    Fill chunk_ids with the ids of the chunks sent."""
    allowed = {c.id for c in chunks}
    system = llm.build_system(llm.load_prompt("explainer"))
    messages = build_messages(app, report, chunks)
    text, bad = "", []
    for attempt in range(1, max_attempts + 1):
        text = llm.text_of(llm.call("policy_check", messages, system=system, max_tokens=900))
        bad = invalid_citations(text, allowed)
        if not bad:
            return Explanation(text, find_citations(text), attempt, [c.id for c in chunks])
        messages = messages + [{"role": "assistant", "content": text},
                               {"role": "user", "content": f"These citations are not in the provided policy chunks: "
                                                           f"{', '.join(bad)}. Rewrite without them; cite only ids "
                                                           "from the <policy_chunk> blocks."}]
    for cid in bad:
        text = text.replace(f"[{cid}]", "[citation removed: not in retrieved policy]")
    return Explanation(text, find_citations(text), max_attempts, [c.id for c in chunks], bad)
