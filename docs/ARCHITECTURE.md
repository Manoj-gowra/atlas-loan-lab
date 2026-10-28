# Architecture: the Atlas case-file assistant

The four-stage shape from lesson 1.4: input -> processing -> output -> feedback. Each box names the module
and the lesson it practises.

```
INPUT        officer uploads a loan package (data/applications/APP-xxx.txt)
               |
PROCESSING   input screening: injection + PII redaction, fail secure ........ guardrails.py      (5.1)
               |
             intake: ONE bounded call, forced tool, schema, retry ............ extraction.py     (1.2, 2.3)
               |      haiku, few-shot prompt, cached system prompt ........... llm.py, prompts/  (2.1, 2.4)
             semantic checks (plausibility the schema can't express) ......... diagnosis.py      (4.3)
               |
             policy check = WORKFLOW
               rules in code: DSCR, LTV, score, amount, years ................ rules.py          (2.3)
               retrieve: metadata filter -> BM25 rank ........................ rag.py            (3.3)
               explain with citations, verify, named feedback ................ explain.py        (3.3)
               |
               +-- only if borderline: COORDINATOR (plain code) .............. agents.py         (1.3)
               |      scoped briefs -> 3 specialist AGENTS in parallel ....... coordination.py   (1.3, 3.0)
               |      every tool call through the GATE (authz, fail secure) .. gate.py, authz.py (3.1, 3.2)
               |      synthesis with provenance -> unverified asides labelled
               |
             drafting: memo from a minimised case summary .................... pipeline.py       (5.3)
             output screening: prohibited factors, leaks ..................... guardrails.py     (5.1)
               |
OUTPUT       escalation triggers -> queue + role -> approval packet ......... escalation.py     (5.2)
             HUMAN decides within dollar authority; hash-chained audit ....... approval.py       (5.2, 5.3)
               |
FEEDBACK     officer corrections (original + corrected + context) ........... feedback.py       (1.4)
             -> correction rate per field (alert) ............................. monitoring.py     (3.6)
             -> new regression cases for the eval set ......................... evals.py          (4.1, 4.2)

ACROSS ALL   one trace per application: tier, cache, chunks, tool order, cost, latency ... tracing.py (3.6)
```

## Components and why they are shaped this way

| Component | Pattern | Tier | Why (lesson) |
|---|---|---|---|
| intake | augmented LLM | haiku | Bounded transformation, high volume, officer waiting (1.2, 2.1) |
| policy check | workflow | sonnet (explanation) + code (rules) | Fixed steps; the reasoning is the deliverable; rules must be enforced, not requested (1.2, 2.3) |
| investigation | coordinator + 3 agents | opus | Path depends on findings; independent subtasks; too many tools for one agent (1.2, 1.3) |
| drafting | workflow | sonnet | Fixed path; officer edits; screened before anyone sees it (1.2, 5.1) |
| decision | human | none | High impact, irreversible, regulated (1.1, 5.2) |
| judge (evaluation only) | augmented LLM | sonnet | One bounded scoring call against observable criteria (4.1) |

## Trust boundaries

- Document text is **untrusted data**: delimited in `<document>` tags, screened, and read by a component
  (intake) that holds **no data tools** (privilege separation, 5.1).
- Every tool call passes `gate.execute_tool()`: grant -> case scope -> officer portfolio, enforced in code
  at execution time (3.2). An authorization outage denies (fail secure).
- Only `ApprovalGate` can set a status, and only within the approver's lending authority (2.3, 5.3).
  Nothing in the AI system can reach `disburse_funds`.
- Guarantor SSN, date of birth and home address are redacted before the model and before logs (5.3).

## External sources as MCP

`atlas/mcp_server.py` exposes the bureau, filings and industry sources over MCP, per client (3.4).
`atlas/ops_mcp.py` gives a debugging assistant read-only access to traces and the change log (7.2).
Both are registered for Claude Code in `.mcp.json`.
