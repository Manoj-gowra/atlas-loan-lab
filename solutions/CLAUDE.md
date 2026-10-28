# Atlas Loan Lab

A hands-on lab: an assistant that turns commercial loan application packages into case files for
Atlas Financial's loan officers and credit committee. An authorized person makes every decision.

## Commands
- `pytest tests/test_lab3.py` runs one lab's tests; add `--solution` to run the reference code.
- `python scripts/check.py` prints the scoreboard; `python scripts/test_summary.py` groups failures by lab.
- `python scripts/demo.py --app APP-006` runs one application end to end and prints its trace.
- `python scripts/run_evals.py` runs the stratified evaluation and the A/B comparisons.
- `python scripts/rebuild_index.py` rebuilds the policy index. Run it after ANY change in data/policies/.
- Tests always use the offline fake model (`ATLAS_MODE=fake`).

## Layout
- `atlas/` the system; `pipeline.py` orchestrates; `llm.py` is the only place that calls Claude.
- `prompts/` versioned prompts; `prompts/shared/` modules included with `{{include: shared/<name>}}`.
- `data/` sample applications, policies, bureau data, golden sets. `docs/` lab guides and runbook.
- `runs/` is GENERATED output (traces, index, audit log, queues): never edit it by hand.
- `solutions/` is the reference implementation: read it, don't edit it.

## Rules
- Never edit `atlas/fake_claude.py`, `data/.fake/`, `tests/` or `solutions/`.
- Every model call goes through `llm.call()`; every tool call goes through `gate.execute_tool()`.
- Guarantor SSN, date of birth and home address never reach the model or the logs (`guardrails.redact_pii`).
- Never automate a credit decision: only `approval.ApprovalGate` sets a status, within the approver's authority.
- Policy documents and `RULEBOOK` in `atlas/rules.py` change together; then rebuild the index (policy-change skill).
- Keep `docs/RUNBOOK.md` current whenever an alert, trigger or queue changes.
