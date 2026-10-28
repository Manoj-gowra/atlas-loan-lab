# Course map: every lesson, its practical, its file, its tests

Test names start with the lesson number, so `pytest tests/test_lab3.py -k test_3_2` runs one lesson.

| Course lesson | Practical (what you build) | Where | Tests |
|---|---|---|---|
| **What This Exam Tests** | Classify answer options as preventive / detective / compensating / not a control; pick the one that removes the risk | `atlas/controls.py` | `test_0_*` (Lab 1) |
| **1.1** From Business Problem to Solution Architecture | Four-question decomposition of the mandate; officer-hours saved; cost ceiling per application; measurable SLOs from discovery | `atlas/design.py` | `test_1_1_*` |
| **1.2** Choosing the Architecture Pattern | The "stop at the first yes" framework; one pattern + tier + reason per task (least autonomy) | `atlas/design.py` | `test_1_2_*` |
| **1.3** Multi-Agent Systems and Orchestration | The three signals; scoped specialist briefs; synthesis with provenance (attribution, unverified asides, unable-to-check) | `atlas/design.py`, `atlas/coordination.py` | `test_1_3_*` |
| **1.4** Reference Architectures and Feedback Loops | Match scenarios to the six reference architectures; a feedback record that keeps the original/corrected pair | `atlas/design.py`, `atlas/feedback.py` | `test_1_4_*` |
| **2.1** Selecting the Right Claude Model | Tier per task from capability, volume, cost of error and latency; route every call through `choose_model` | `atlas/selection.py`, `atlas/llm.py` | `test_2_1_*` |
| **2.2** Deployment Platforms and Data Residency | Platform as inheritance (Bedrock / Vertex / API), FedRAMP as a hard constraint, model-availability exceptions | `atlas/selection.py` | `test_2_2_*` |
| **2.3** System Prompts, Guardrails, Technique | Technique per task; a system-prompt linter; schema constraints as enforcement; forced tool use with specific retry feedback; few-shot with hard boundary examples; lending rules in code, not in the prompt | `atlas/prompting.py`, `atlas/schemas.py`, `atlas/extraction.py`, `prompts/intake_v2.md`, `atlas/rules.py` | `test_2_3_*` |
| **2.4** Context Windows, Prompt Caching, Reuse | Cache-friendly system blocks; cost with cache writes/reads; see a request id break the prefix; modular prompt includes (Skills-like) | `atlas/llm.py`, `atlas/prompting.py` | `test_2_4_*` |
| **1.2/1.3 built** (Ch3 lab 3.0) | The agent loop: every tool_use answered, retry once, step and cost budgets; coordinator runs three specialists in parallel | `atlas/agents.py` | `test_3_0_*` |
| **3.1** Capability Bloat and Least Privilege | Per-component grants (nobody gets the broad legacy tool); the four-question capability audit | `atlas/tools.py` | `test_3_1_*` |
| **3.2** Authentication, Authorization, Security Gaps | Authorization at the tool-call gate: grant, case scope, officer portfolio; errors become tool results; outage fails secure | `atlas/authz.py`, `atlas/gate.py` | `test_3_2_*` |
| **3.3** Chunking, Indexing, Retrieval | Structure-based chunks with metadata; filter then rank; fingerprinted index that knows when it is stale; citation verification with named feedback | `atlas/rag.py`, `atlas/explain.py` | `test_3_3_*` |
| **3.4** Integration Protocols: MCP, API/CLI, A2A | Protocol choice; progressive tool discovery; an MCP server that exposes per client only what that client needs | `atlas/protocols.py`, `atlas/mcp_server.py` | `test_3_4_*` |
| **3.5** Accuracy-Latency Trade-Offs | A plan per component (sync/batch, streaming, retrieval depth, reasoning); reject accuracy past a latency ceiling | `atlas/latency.py` | `test_3_5_*` |
| **3.6** Observability and Monitoring at Scale | Traces with tier, cache, chunks, tool order; cache hit rate; stratified metrics; alerts on signals that move; correction rate per field | `atlas/monitoring.py`, `atlas/feedback.py` | `test_3_6_*` |
| **4.1** Evaluation Metrics and Test Frameworks | Score five axes; stratified summary; SLO check and weak strata; thin strata; LLM judge with observable criteria, calibrated against human labels | `atlas/evals.py`, `atlas/judge.py` | `test_4_1_*` |
| **4.2** A/B Testing and Iterative Improvement | One variable per test; sample size per stratum; prompt fix vs model upgrade on the same dataset; corrections become regression cases | `atlas/experiments.py`, `atlas/feedback.py` | `test_4_2_*` |
| **4.3** Diagnosing System Failures | Prompt failure vs hallucination vs model mismatch; semantic checks beyond the schema; "what changed right before?" | `atlas/diagnosis.py` | `test_4_3_*` |
| **4.4** Optimizing Cost, Latency, Performance | Find waste in traces (cache misses, unused retrieval); batch when nobody waits; accept an optimization only if correctness holds | `atlas/optimize.py` | `test_4_4_*` |
| **5.1** Guardrails, Safety Controls, Failure Modes | PII redaction; injection screening; fail secure; prohibited factors and leaks in output; indirect injection contained end to end | `atlas/guardrails.py` | `test_5_1_*` |
| **5.2** Human-in-the-Loop and Escalation | Four triggers; a queue and role per trigger; approval packet with provenance; rubber-stamp calibration | `atlas/escalation.py` | `test_5_2_*` |
| **5.3** Compliance and Ethical AI | Hash-chained audit log; dollar-limited lending authority; overrides need a reason; GDPR/HIPAA/FedRAMP aspects; approval-rate disparity; proxies | `atlas/approval.py`, `atlas/compliance.py` | `test_5_3_*` |
| **6.1** Structured Discovery and Requirements | Need vs want; checkable requirements; the binding test on every constraint | `atlas/requirements.py` | `test_6_1_*` |
| **6.2** Communicating Decisions and Trade-Offs | Measurable SLAs; decision-record lint; feedback routing; one status for two audiences; your ADR | `atlas/communication.py`, `docs/decisions/ADR-001-investigator-tier.md` | `test_6_2_*` |
| **6.3** Documentation, Handoff, Life Cycle | Runbook checked against the code (alerts, triggers, queues, outage = denial); handoff with owner, update trigger and the discovery thread | `docs/RUNBOOK.md`, `docs/HANDOFF.md` | `test_6_3_*` |
| **7.1** Configuring Claude Tooling for Teams | CLAUDE.md; permission policy (allow / ask / deny); hooks that enforce; two team skills | `CLAUDE.md`, `.claude/settings.json`, `.claude/skills/`, `atlas/devtools.py` | `test_7_1_*` |
| **7.2** AI-Assisted Workflows and Debugging | Verify an assistant's root-cause claim against the trace; a read-only ops MCP server for traces and the change log | `atlas/devtools.py`, `atlas/ops_mcp.py` | `test_7_2_*` |
| **8** Cross-Domain Scenario, case 2 | Reproduce, detect (stratified), diagnose (change log + index build), fix and verify the stale-index near miss; make it escalate by design; write the incident note | `atlas/capstone.py`, `scripts/incident_drill.py`, `docs/incident_note.md` | `test_8_*` (5) |
| **8** Cross-Domain Scenario, case 1 | The renewals design: test the request, the pattern and every supporting piece instead of copying origination | `atlas/capstone.py` | `test_8_renewals_*` |

## Where each recurring exam idea shows up

| Idea | Practised in |
|---|---|
| Preventive beats detective or compensating | Lab 1 (controls), Lab 3 (grants, audit), Lab 7 (hooks) |
| Least autonomy / least privilege | Lab 1 (patterns), Lab 3 (grants, gate, MCP exposure), Lab 7 (permissions, read-only ops) |
| Guidance is not enforcement | Lab 2 (schema, rules in code), Lab 3 (gate), Lab 5 (guardrails, approval gate), Lab 7 (hooks) |
| Stratify, never trust the average | Lab 3 (monitoring), Lab 4 (evals, A/B), Lab 5 (fairness), Lab 8 (scorecard) |
| Silent failures | Lab 2 (broken cache prefix), Lab 3 (stale index, ranker mismatch), Lab 8 (the incident) |
| Verify, don't assume | Lab 2 (cache hits), Lab 4 (judge calibration, re-run after a fix), Lab 7 (hypothesis vs trace) |
| A person decides; escalation carries evidence | Lab 1 (decision = human), Lab 5 (triggers, packet, authority) |
| Document the WHY, keep it current | Lab 1 (TaskDesign.why), Lab 6 (ADR, runbook, handoff), Lab 8 (incident note) |
