# Atlas case-file assistant: handoff package

Owner: Credit Platform team lead (Sam Ortiz is the business owner)
Update trigger: any change to a requirement, a constraint, an SLA, a component's pattern or model tier, or a
runbook entry. The change and the update to this file ship in the same pull request.

Course link: lesson 6.3. This file consolidates the documentation thread that started in discovery: it is
assembled from `atlas/requirements.py` (discovery), `atlas/design.py` and `docs/decisions/` (design) and
`docs/RUNBOOK.md` (operations). It is not written from memory.

## 1. The need

Cut the officer time spent on standard-case paperwork (retyping figures and looking up policy) so officers
can give borderline applications the judgment they need. The stated want was "an AI that reads loan
documents"; the need underneath it is officer time on the routine majority (about 4,000 applications a
year, 90 minutes each, two-thirds of it removable: about 4,000 officer-hours a year).

## 2. Requirements and constraints (validated with the stakeholders on 2026-09-08)

| Id | Requirement | How it is checked | Target |
|---|---|---|---|
| R1 | Case file ready soon after upload | p95 seconds from upload to case file | <= 60 |
| R2 | Extracted figures are trustworthy for every document type | field accuracy per document type | >= 0.95 |
| R3 | Applications are routed correctly | route accuracy | >= 0.90 |
| R4 | Few files need a manual field check | share of applications with fields to review | <= 0.30 |
| R5 | Running cost stays within budget | average model cost per application (USD) | <= 0.05 |
| R6 | Escalations reach the committee with evidence | approval packets with evidence attached | 100% |

| Id | Constraint | Binding? | Why (the owner's answer to "what if it can't be met?") |
|---|---|---|---|
| C1 | Integrate with the current loan-origination platform | Binding | Replacing the LOS is a multi-year programme: we'd revisit the whole approach |
| C2 | Applicant data stays inside the bank's AWS account | Binding | Cannot: that is how the bank passed the regulator's cloud review |
| C3 | A person makes every credit decision | Binding | Cannot: policy 3.1 and fair-lending law |
| C4 | Show results in the Lending Hub dashboard | Preference | Preferred; an equivalent view would be fine |
| C5 | Build it in Python | Preference | Nice to have; could work around it |

## 3. Service levels (what the evaluation checks against)

- Speed: 95% of case files are ready within 60 seconds of upload.
- Accuracy: at least 95% of extracted fields are correct, reported per document type and per loan type.
- Routing: at least 90% of applications go down the correct path.
- Officer checks: at most 30% of files need an officer to confirm a field.
- Cost: on average at most $0.05 of model usage per application.

`python scripts/run_evals.py` reports every one of these, overall and per stratum.

## 4. Architecture at a glance (the WHY is the part that must survive)

| Component | Pattern | Model tier | Why |
|---|---|---|---|
| intake | augmented LLM | haiku | One document in, one schema out: a bounded call on a compact model, verified on messy scans with a few-shot prompt. |
| policy_check | workflow | sonnet | Fixed steps: retrieve the sections, check rules in code, explain with verified citations. A regulator must be able to follow the reasoning. |
| drafting | workflow | sonnet | A fixed path assembles the facts and drafts the memo; the officer edits every word and output screening runs before anyone sees it. |
| investigation | agent (coordinator + 3 specialists) | opus | Where to look depends on what is found; it runs only for borderline cases, so volume is low and a shallow answer is costly. Decision record: `docs/decisions/ADR-001-investigator-tier.md`. |
| decision | human | none | Approving or declining credit is high impact, irreversible and regulated; the approval gate enforces dollar-limited authority. |

Platform: Amazon Bedrock inside the bank's existing AWS account (inherits the regulator-reviewed environment,
constraint C2). The investigator's tier must be confirmed as available on Bedrock before each model upgrade;
if it is not, the documented exception is to keep the previous tier, never to call another platform.

## 5. Operating it

- Runbook: `docs/RUNBOOK.md` (alerts, escalation queues and roles, failure modes, routine operations).
- Team tooling: `CLAUDE.md`, `.claude/settings.json`, the skills in `.claude/skills/`, `.mcp.json`.
- Switching from the offline model to real Claude: `ATLAS_MODE=anthropic` with an API key in `.env`; re-run
  the evaluation before trusting any number.

## 6. Life cycle: what to update when

| Phase | Artifact | Updated when |
|---|---|---|
| Discovery | `atlas/requirements.py`, section 2 above | A stakeholder's need or a constraint changes |
| Design | `atlas/design.py`, `docs/decisions/` | A pattern, tier or platform decision changes |
| Handoff | this file | Any of the above, in the same pull request |
| Monitoring | `docs/RUNBOOK.md`, `atlas/monitoring.py` | An alert, trigger, queue or threshold changes |
| Iteration | all of the above | After every incident (`docs/incident_note.md`) |
