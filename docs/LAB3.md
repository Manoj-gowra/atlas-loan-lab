# Lab 3: Integration

Course: Chapter 3 (lessons 3.1 to 3.6), plus the agent loop behind lessons 1.2/1.3 · Time: about 3 hours ·
Tests: 37 · Needs: Labs 1-2

The biggest lab. By the end the whole pipeline runs end to end: three specialist agents in parallel, every
tool call authorized at a gate, retrieval that filters on metadata and knows when its index is stale,
citations verified in code, an MCP server scoped per client, latency plans per component, and traces you
can monitor.

```bash
pytest tests/test_lab3.py
python scripts/check.py 3
```

---

## Exercise 3.0: The agent loop (lessons 1.2 and 1.3, built)

**The idea**
- An agent is an augmented LLM in a loop: call the model with its tools, run EVERY `tool_use` it asked
  for, send ALL results back in ONE user message (one `tool_result` per `tool_use` id), repeat until it
  calls `submit_findings`.
- The stop condition lives in CODE: a step budget and a cost budget. Hitting either escalates; it never
  "keeps trying".
- The coordinator here is plain code: it always dispatches the same three roles in parallel (an
  enumerable fan-out). Its synthesis is yours from Lab 1.

**Practical:** `atlas/agents.py` `run_specialist()`. Read `investigate()` (given) to see the parallel
fan-out, the scoped briefs and the `tagged(group=..., member=...)` trace tags.

The offline model will: call two tools at once, hit a bank-service timeout and retry once (APP-006), try to
look up an affiliate's record outside the case (APP-006), and loop forever widening a search (APP-007).

**Check:** `pytest tests/test_lab3.py -k test_3_0`

---

## Lesson 3.1: Capability bloat and least privilege in tool configuration

**The idea**
- Capability bloat is access beyond the CURRENT task. It accumulates quietly: a tool left over after a
  scope change, a shared registry where every agent got every tool, a broad admin credential "for now".
- Least privilege REMOVES the capability. Logging it (detective) or confirming it (compensating) leaves
  the exposure in place. A prompt line saying "don't use it" is not removal.
- A tool description growing "do not use this to..." warnings means the tool does too much: split it.
- Audit each capability: does the current task need it? Does the component still work without it? Was it
  granted deliberately or inherited? Is misuse disproportionate to the component's scope? Fail any: remove.

**Practical:** `atlas/tools.py`
1. Read `manage_loan_record` in `TOOL_DEFS`: the warnings tell you it should never be granted.
2. `GRANTS`: one deliberate entry per component. Intake, explainer and drafting call no data tools.
3. `audit_grants()`: the four questions as code.

**Check:** `pytest tests/test_lab3.py -k test_3_1`

---

## Lesson 3.2: Authentication, authorization and security gaps

**The idea**
- Authentication: WHO is calling. Authorization: WHAT that identity may do. A strongly authenticated
  intake service says nothing about whether it may change a disbursement status.
- Authorization is enforced at the DISPATCH / TOOL-CALL GATE, in code, at execution time, against the
  caller's role and session scope. Never by a prompt ("only access this applicant's records"), a UI
  restriction or the caller's own claim.
- Session scope: an AI acting for a loan officer must not see more than that officer. Atlas officers work
  a regional portfolio.
- Per-component credentials, not one shared service account.

**Practical**
1. `authz.AuthorizationService.check()`: grant, then the case's customer, then the officer's portfolio.
2. `gate.execute_tool()`: authorize first (an outage FAILS SECURE: deny), then dispatch, and turn every
   failure into a `tool_result` the model can read. It never raises.

**Check:** `pytest tests/test_lab3.py -k test_3_2`

**Exam trap:** "the agent is authenticated with mTLS, so the call is safe". AuthN is not authZ.

---

## Lesson 3.3: Chunking, indexing and retrieval for a RAG pipeline

**The idea**
- RAG is a chain of independent decisions (chunk, index, retrieve, generate), and each can fail silently.
- Chunk by SOURCE STRUCTURE: the policy manual is numbered rules, so one rule per chunk. A fixed 200-token
  window can cut a rule from its exception.
- Store metadata on every chunk (loan type, jurisdiction, effective dates) and FILTER on it first, then
  rank. Similarity has no idea which version is in force. Exact thresholds favour keyword ranking.
- Two silent failures: a STALE INDEX (source updated, index not rebuilt) and MISMATCHED EMBEDDINGS or
  ranker (query side upgraded, index built by the old one). Both return confident wrong answers. Make
  staleness detectable.
- Grounding: answer only from retrieved text, and CHECK every citation in code. An invented citation is
  a hallucination you can detect; name it in the retry, and strip and flag it if it persists.

**Practical**
1. `rag.chunk_policy()` and `rag.is_applicable()`.
2. `rag.PolicyIndex.build()` and `is_stale()`: fingerprints per file plus the ranker version.
3. `rag.retrieve()`: filter, BM25, drop zeros, top k.
4. `explain.build_messages()`, `invalid_citations()` and `explain()`: generate, verify, named feedback,
   strip and flag.

**Check:** `pytest tests/test_lab3.py -k test_3_3`

**Exam trap:** the answer cites an outdated rule from the wrong product, and metadata exists. Fix:
metadata filtering, not more passages or a better query.

---

## Lesson 3.4: Integration protocols: MCP, API/CLI, agent-to-agent

**The idea**
- MCP earns its overhead when a capability is REUSED across agents or clients, or the set GROWS or
  CHANGES. A direct API/CLI call suits one stable, well-understood connection. Agent-to-agent is for a
  genuinely AUTONOMOUS peer outside your control (a partner bank's AI on a syndicated loan): you send a
  goal, across a real boundary.
- Atlas: intake's document service = direct API; the investigator's evolving bureaus and public records =
  MCP; a partner bank = agent-to-agent.
- Progressive discovery: with many tools, load only the definitions the task needs.
- Protocol choice never replaces least privilege: an MCP server should expose per client only what that
  client needs.

**Practical**
1. `protocols.choose_protocol()` and `protocols.select_tools()`.
2. `mcp_server.CLIENT_EXPOSURE` and `build_server()`: register only the exposed tools, each annotated
   read-only. (Tests skip if `mcp` isn't installed.)

**Check:** `pytest tests/test_lab3.py -k test_3_4`

**Try it in Claude Code:** `.mcp.json` registers this server for Claude Code with the `claude_code`
exposure. Run `/mcp` in Claude Code and see which tools it can discover.

---

## Lesson 3.5: Accuracy-latency trade-offs

**The idea**
- "Fast and accurate" hides a decision. Five levers: model tier, STREAMING (perceived latency only, costs
  no accuracy, reach for it first), batch vs synchronous (is anyone waiting?), retrieval depth and
  reasoning effort.
- Pick the point that clears the accuracy bar inside the latency ceiling, and reject a more accurate
  design that breaks the ceiling. Intake has an officer watching; the investigator has nobody watching
  live; nightly re-scoring has a deadline, not a wait.

**Practical:** `atlas/latency.py`: `COMPONENT_PLANS`, `check_plan()` and `perceived_wait_s()`.

**Check:** `pytest tests/test_lab3.py -k test_3_5`

---

## Lesson 3.6: Observability and monitoring at scale

**The idea**
- Uptime and error rate answer "did it complete". LLM systems also need "was it right, and did it cost
  what it should?" Three challenges: non-determinism (a clean retry proves little), silent quality
  regressions (stale index, changed document format) and cost drift (a broken cache prefix).
- A trace must capture the model tier, cache hit/miss, which chunks retrieval returned, which tools ran
  in what order, tokens, cost and latency.
- Stratify: 94% overall can hide 60% on one document type.
- Alert on signals that move: a rising correction rate on ONE field, a falling cache hit rate, cost per
  call drifting up. The feedback loop is your early warning.

**Practical**
1. `monitoring.cache_hit_rate()`, `stratify()`, `evaluate_alerts()` and `should_close_ticket()`.
2. `feedback.FeedbackStore.correction_rate_by_field()`.

**Check:** `pytest tests/test_lab3.py -k test_3_6`

---

## See it work

```bash
python scripts/demo.py --app APP-006     # the full borderline case and its trace
python scripts/demo.py --app APP-007     # an agent that hits its step budget
python scripts/demo.py                   # all ten applications, cost and time per case
```

In APP-006's trace, find the bank call that timed out and its retry, the denied B-1012 look-up, the
`cache=hit` lines, and the retrieval chunk ids. Then open `runs/traces/APP-006.jsonl`.

## Say it out loud

1. Walk through one turn of the agent loop. What breaks if two tool results go back in two messages?
2. The intake agent still has a tool that can change approval status. Logging, confirmation or removal?
3. The assistant serves a loan officer who works California only. A New York case comes in. What happens,
   where is it enforced, and why not in the prompt?
4. The authorization service times out. What does the gate do, and why is that correct?
5. Why one chunk per numbered rule? What two silent failures make RAG answer confidently and wrongly?
6. Bureau data for the investigator, a stable internal document service, a partner bank's AI: which
   protocol for each?
7. A slower second verification pass raises intake accuracy by 0.5% and doubles the wait. Ship it?
8. Overall accuracy is 94% and stable. Why might you still page someone?
