---
name: policy-change
description: Apply a lending policy change (a new threshold, limit, rate or jurisdiction rule) consistently across the policy documents, the rules engine, the search index, the tests and the runbook. Use whenever someone asks to change or add a lending rule.
---

# Policy change

Policy lives in places that must always agree: the documents in `data/policies/` (what retrieval finds
and explanations cite), `RULEBOOK` in `atlas/rules.py` (what the code enforces) and the search index
built from the documents.

1. Never edit the version in force. Copy `data/policies/<product>_vN.md` to `<product>_v(N+1).md`, bump
   `version`, set `effective_from`, and set `effective_to` on the old file to the day before.
2. In `atlas/rules.py`, close the old `ProductRules` and add the new one with the same dates.
3. Rebuild the index: `python scripts/rebuild_index.py`. A stale index makes explanations cite the old
   threshold while the code applies the new one (Lab 8).
4. Check every `policy_ref` the rules produce exists in the index.
5. Add tests for one application before and one after the effective date; run `pytest` and
   `python scripts/run_evals.py` and compare the affected loan type's stratum with the last run.
6. Update `docs/RUNBOOK.md` if thresholds an alert depends on changed, and write a three-line summary
   for Compliance: what changed, from when, which applications it affects.
