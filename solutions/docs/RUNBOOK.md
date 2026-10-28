# Atlas case-file assistant: operations runbook

Owner: Credit Platform team (on-call: platform-oncall) · Update trigger: any change to `monitoring.ALERTS`,
`escalation.TRIGGERS`, `escalation.QUEUES`, a policy document or the index build job.
Course link: lesson 6.3 (operational guidance), with 3.6 (alerts), 5.1 (fail secure) and 5.2 (queues).

## 1. Alerts: what each one means and what to do

| Alert id | What it means (the failure mode behind it) | First response | Who is paged |
|---|---|---|---|
| `correction_rate_spike` | Officers are correcting ONE field far more than its baseline. Usually a changed document format or a stale policy index, not a model problem. | Stratify corrections by field, document type and loan type. Check `get_change_log` for a policy publication or index build in the 72 hours before the rise. | ML on-call |
| `cache_hit_rate_drop` | A stable prompt prefix stopped being reused: something variable (a timestamp, a request id, applicant data) moved into or in front of the cached block. Cost and latency rise with no error. | Diff the system prompt of the affected task against the last good deploy; move the variable part after the cache breakpoint (`llm.build_system`). | Platform on-call |
| `cost_per_call_drift` | One component's cost per call is climbing: a broken cache prefix, deeper retrieval, growing agent loops or a tier change. | Read cost per task in the traces; compare model, cached tokens and step counts with the baseline week. | Platform on-call + Finance partner (FYI) |

Alerts are evaluated by `atlas.monitoring.evaluate_alerts` against the baseline week (factor 2).
A clean retry never closes an alert ticket on its own: check for similar reports in the last 30 days.

## 2. Escalation triggers: which queue, which role

| Trigger | Queue | Role that picks it up | What the reviewer does |
|---|---|---|---|
| `high_impact` | `senior-review` | `senior_credit_officer` | Decide within their authority (up to $2,000,000); above that, take it to the credit committee. Every decline needs the policy sections that justify it. |
| `policy_gap` | `policy-exceptions` | `credit_risk_committee` | No written rule covers the case. Decide the case, then ask Compliance whether the policy needs a new rule. Never apply the "closest" rule. |
| `conflicting_evidence` | `verification` | `loan_officer` | Resolve the conflict from source documents (stated vs verified EBITDA, specialists that disagree, a citation that does not match the rule applied). Never pick one side or average. |
| `low_confidence` | `field-review` | `loan_officer` | Confirm the listed fields against the document; for a tampered document or a held screening, re-run intake manually. |

Every escalated case carries an approval packet: the action, the evidence with its source, the triggers,
the system's recommendation and reasoning. If a packet is empty, that is a bug: page Platform on-call.

Calibration: once a month, compare reviewers' decisions with the system's recommendations. Agreement of
98% or more with a median review under 30 seconds (`escalation.rubber_stamp_risk`) means reviewers are
rubber-stamping: reduce volume or sharpen the triggers.

## 3. Failure modes that are CORRECT behaviour

- **Authorization service outage.** The tool-call gate denies every call (fail secure). Investigations come
  back with "unable to check" items and no automated recommendation. Treat it as a DENIAL to investigate,
  not a bug to route around: never bypass the gate, never re-run with broader credentials. Page Platform
  on-call; officers process affected cases manually until the service is back.
- **Screening service outage.** Input screening fails secure: the case is held with the flag
  `screening_unavailable` and a `low_confidence` trigger. Re-run the case after the service recovers.
- **Agent budget exhausted.** A specialist stopped at its step or cost budget (`agent_escalated`). The case
  goes to `field-review`; look at the trace to see where it looped before raising any budget.
- **Citation removed.** The explainer cited a section it was not given; the citation was stripped and the
  case flagged. If this rises for one loan type, check the index freshness first.

## 4. Routine operations

- **Policy update** (Compliance publishes a new version): follow the `policy-change` skill. The index MUST be
  rebuilt in the same change (`python scripts/rebuild_index.py`); confirm `PolicyIndex.is_stale()` is False
  and that the nightly build log shows the run. A skipped rebuild produces explanations that cite the old
  threshold with no error anywhere (incident 2026-11, see `docs/incident_note.md`).
- **Prompt or model change**: run `python scripts/run_evals.py` and compare every stratum, not only the
  overall line. One variable per change.
- **Traces**: `runs/traces/<APP-ID>.jsonl`, PII redacted. Read-only access through the `atlas-ops` MCP server.
