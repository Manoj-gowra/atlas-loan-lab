# Atlas Loan Lab

A hands-on companion to the Educative course **Master Claude Certified Architect – Professional (CCAR-P)**.
You build the course's running case study, the **Atlas Financial commercial-lending assistant**, one course
chapter at a time. Every lesson in the course has a practical here, with tests that tell you when it works.

It runs **free and offline**. A simulated Claude (`atlas/fake_claude.py`) behaves like the Messages API,
including the failures the course warns about: confidently wrong extractions, invented citations, prompt
injection, a timed-out service, a looping agent, broken prompt caching. When you have an API key, set
`ATLAS_MODE=anthropic` and the same code talks to real Claude.

## What you build

An officer uploads a commercial loan package. The system:

1. screens the document (injection, personal data), extracts the fields (augmented LLM, structured output),
2. checks the lending policy in code and explains the result with verified citations (workflow + RAG),
3. for borderline cases, runs a coordinator with three specialist agents in parallel (multi-agent),
4. drafts a memo, screens it, and routes the case to the right human queue with an approval packet,
5. records every decision in a tamper-evident audit log, within each approver's dollar authority.

Then you prove it (stratified evals, an LLM judge calibrated by human labels, A/B tests), operate it
(alerts, runbook, handoff) and configure Claude Code for the team. The capstone replays the course's
near-miss incident: a stale policy index that the dashboard average hides.

## The eight labs (one per course chapter)

| Lab | Course chapter | You practise | Tests | Time |
|---|---|---|---|---|
| 1 | Ch1 Solution design and architecture (+ What This Exam Tests) | controls, decomposition, value, SLOs, pattern choice, multi-agent provenance, reference architectures, feedback loops | 33 | 1.5 h |
| 2 | Ch2 Models, prompting and context engineering | tier per task, platform inheritance, instruction hierarchy, few-shot, schema as enforcement, rules in code, prompt caching, modular prompts | 43 | 2.5 h |
| 3 | Ch3 Integration | agent loop, least privilege, authN vs authZ at the gate, RAG with metadata and staleness, MCP vs API vs A2A, latency levers, observability | 37 | 3 h |
| 4 | Ch4 Evaluation, testing and optimization | five eval axes, stratification, LLM judge + human calibration, A/B with one variable, diagnosis, waste and batch | 25 | 2 h |
| 5 | Ch5 Governance, safety and risk | input/output screening, fail secure, indirect injection, four escalation triggers, approval packets, audit chain, fairness | 37 | 2 h |
| 6 | Ch6 Stakeholder communication and life cycle | need vs want, binding test, two-audience summaries, decision record, runbook, handoff | 23 | 1.5 h |
| 7 | Ch7 Developer productivity and enablement | CLAUDE.md, permissions, hooks, skills, MCP for debugging, verifying an AI's hypothesis | 9 | 1 h |
| 8 | Ch8 Capstone | the stale-index near miss end to end, and the renewals design | 6 | 1.5 h |

Do them in order: each lab builds on the previous ones. `docs/COURSE_MAP.md` maps every course lesson to
its practical, its file and its test.

## Setup (Mac / Linux, Python 3.10+)

```bash
cd atlas-loan-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check.py                 # everything "not started"
python scripts/check.py all --solution  # the reference solution: all green
```

## How to work a lab

1. Read `docs/LAB<n>.md`: a short recap of each lesson, then the exercise for it.
2. Open the files it names. Every exercise is a `TODO (Lab n)` that raises `NotImplementedError`.
3. Run `pytest tests/test_lab<n>.py` (or `python scripts/check.py <n>` for details) until it is green.
   Test names start with the lesson number, e.g. `test_3_2_the_gate_never_executes_an_unauthorized_call`.
4. Run the "see it work" command in the guide and look at what your code produced.
5. Answer the "say it out loud" questions at the end of the guide without looking. That is the exam.

Stuck? `solutions/` holds the reference implementation. Read it, don't copy it: typing it yourself is
what makes it stick.

## Useful commands

| Command | What it does |
|---|---|
| `python scripts/check.py` | Scoreboard for all eight labs |
| `python scripts/test_summary.py` | Failing tests grouped by lab (the Lab 7 team workflow) |
| `python scripts/demo.py --app APP-006` | One application end to end: rules, explanation, investigation, packet, memo, trace |
| `python scripts/run_evals.py` | Stratified evaluation and two A/B tests, with executive and technical summaries |
| `python scripts/rebuild_index.py` | Rebuild the policy index (after any policy change) |
| `python scripts/incident_drill.py --fix` | The Lab 8 incident, reproduced and fixed in a sandbox |

Add `--solution` to any script to run the reference implementation.

## Using Claude Code on this project

The repo is set up the way the course recommends for teams (Lab 7): `CLAUDE.md`, `.claude/settings.json`
(permissions and hooks), `.claude/skills/` and `.mcp.json`. Open the folder in Claude Code and ask it to
explain a failing test. Ask it to hint, not to solve: the point is that you can explain every line.

## Switching to real Claude

```bash
cp .env.example .env     # then set ATLAS_MODE=anthropic and ANTHROPIC_API_KEY=...
python scripts/demo.py --app APP-001
```

Tests always use the offline model, so they stay deterministic and free. Real Claude reads the documents
instead of an answer key, so expect small differences, and re-run the evals before trusting any number.

## Map of the repo

```
atlas/        the system (your code): one module per concept, each names its course lesson
prompts/      versioned prompts; prompts/shared/ holds modules included with {{include: shared/x}}
data/         10 sample applications, 3 drill applications, policies, bureau data, golden sets
docs/         lab guides, course map, architecture, discovery notes, runbook, handoff, decisions
tests/        one file per lab, tests named by lesson
scripts/      check, demo, evals, index rebuild, incident drill, Claude Code hooks
solutions/    the reference implementation
runs/         generated output: traces, index, audit log, queues (safe to delete)
```

All people, companies, customers and figures in `data/` are fictional.
