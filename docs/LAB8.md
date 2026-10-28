# Lab 8: Capstone, the cross-domain scenario

Course: Chapter 8 (cross-domain scenario, comprehensive assessment) · Time: about 1.5 hours · Tests: 6 ·
Needs: Labs 1-7

Two cases from the course, each touching every domain. The first you live through: the near-miss
regression, reproduced in a sandbox with your own code. The second you design: the renewals request.

```bash
pytest tests/test_lab8.py
python scripts/check.py 8
```

---

## Case 2: the near-miss regression (do this first)

**The story.** Two weeks after a routine policy update, explanations for agricultural equipment loans cite a
threshold that no longer matches current policy. The dashboard's overall numbers look healthy. A loan officer
catches one just before credit committee.

**Step 1: reproduce and detect.**

```bash
python scripts/incident_drill.py
```

The drill copies the policies into `runs/drill/`, builds the index on 2026-10-27, then Compliance publishes
POL-AGEQ v4 (DSCR minimum 1.20 -> 1.35 from 2026-11-01) and the nightly rebuild is SKIPPED. Three ag
applications arrive. Read the output: which loan type is affected, and why the average would hide it?

**Step 2: diagnose.** The drill runs `diagnosis.what_changed()` (Lab 4) over the change log and checks
`PolicyIndex.is_stale()` (Lab 3). Nothing errored. The prompt, the model and the code were unchanged. What
changed right before the regression?

**Step 3: make the design catch it.** The course's fix list ends with "update the escalation-trigger
definitions so a citation that far out of step with current policy gets caught automatically". Implement
`atlas/capstone.py` `citation_conflicts()`: a citation of the same policy section in a DIFFERENT version
than the rule the engine applied. `escalation_triggers()` (Lab 5) already calls it, so these cases now
fire `conflicting_evidence` without depending on an officer's diligence.

**Step 4: fix and verify.**

```bash
python scripts/incident_drill.py --fix
```

Rebuild, then re-run the SAME stratified check. Conflicts should drop to zero for the affected loan type
and nothing else should move.

**Step 5: communicate and document.** Write `docs/incident_note.md`: what happened, the timeline, why the
dashboard missed it, the root cause (and the date of the event you found), the fix and its verification,
what changes so DESIGN catches it next time, and what you tell stakeholders, honestly. A near miss caught
by good fortune is not "a minor hiccup".

**Check:** `pytest tests/test_lab8.py -k "citation or stale or reproduce or incident"`

---

## Case 1: the renewals request

**The story.** The small-business team renews revolving credit lines for existing customers: a few
thousand a month, smaller, mostly routine, tracked in a shared spreadsheet, with a backlog that spikes at
quarter-end. A VP asks for "an AI system like the one you already built, but for renewals", live before
next quarter close.

Work it as the course does, then fill `RENEWALS_DESIGN` in `atlas/capstone.py`:

1. Test the request against the need. The error rate is already low; what actually hurts?
2. Choose the pattern from THIS task's shape. Origination needed a coordinator because documents vary
   widely; renewals are standardized. What handles the routine majority, and what handles the few with
   complicating signals (which signals)?
3. Check whether each supporting piece transfers. The renewal policy has several legacy versions in
   circulation: can you reuse the origination index? Which tier for routine and for flagged cases?
4. Build an evaluation set for THIS population, stratified how?
5. The four escalation triggers apply conceptually. Do their definitions transfer as they are?
6. What do you tell the VP you are delivering, honestly, compared with "a copy"?

**Check:** `pytest tests/test_lab8.py -k renewals`

---

## The course's self-evaluation checklist, mapped to what you built

| Checklist item | Where you practised it |
|---|---|
| Test the request against the need | Lab 1 (1.1), Lab 6 (6.1), renewals step 1 |
| Separate binding limits from preferences | Lab 6 `classify_constraint` |
| Choose the pattern from the task's shape | Lab 1 `choose_pattern`, `TASK_DESIGN`, renewals step 2 |
| Scope every capability to the current task | Lab 3 `GRANTS`, `audit_grants`, the gate, MCP exposure |
| Match tier and effort per component | Lab 2 `pick_tier`, Lab 3 `COMPONENT_PLANS` |
| Check whether retrieval and context assumptions transfer | Lab 3 index staleness, renewals step 3 |
| Build a stratified dataset for THIS population | Lab 4 evals, renewals step 4 |
| Spot a regression a steady aggregate hides | Lab 3 `stratify`, Lab 4 `weak_strata`, case 2 |
| Does an existing guardrail or trigger cover the new risk? | Lab 5 triggers, case 2 step 3 |
| Did it work by design or by good fortune? | case 2 incident note |
| Communicate honestly, including what changed | Lab 6 ADR and summaries, case 2 step 5 |
| Capture WHY, not just what | `TaskDesign.why`, ADR, handoff, runbook |
| Team tooling and scoped access | Lab 7 settings, hooks, skills, read-only ops MCP |
| Verify an AI-assisted explanation | Lab 7 `verify_hypothesis`, case 2 step 2 |

## Say it out loud (the final exam warm-up)

1. Why did the dashboard miss the regression, and which signal would have caught it earlier?
2. Prove it was a stale index and not the prompt or the model. What evidence do you show?
3. What changes so the next one is caught by design?
4. The VP wants a copy of the origination system for renewals. What do you build instead, and why is it
   cheaper and just as safe?
5. Which origination pieces do NOT transfer to renewals, and what goes wrong on day one if you reuse them?
