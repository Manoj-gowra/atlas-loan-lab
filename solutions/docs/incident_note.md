# Incident note: stale policy index, agricultural equipment explanations (near miss)

Owner: Credit Platform team lead · Status: closed after verification · Severity: near miss (no wrong decision)

## What happened
From 2026-11-03, policy explanations for agricultural equipment applications cited the superseded POL-AGEQ v3
sections (minimum DSCR 1.20) while the rules engine correctly applied v4 (minimum DSCR 1.35, effective
2026-11-01). APP-101 was flagged as borderline at a DSCR of 1.30, but its explanation quoted the 1.20 minimum.
A loan officer noticed the mismatch before the credit committee met. No decision used the wrong threshold.

## Timeline (UTC)
- 2026-10-27 02:00 nightly index build ran normally.
- 2026-10-28 16:00 Compliance published POL-AGEQ v4 and closed v3 on 2026-10-31.
- 2026-10-29 02:00 nightly index build SKIPPED (job runner out of disk). No alert existed for a skipped build.
- 2026-11-03 to 2026-11-05 three agricultural equipment applications explained with v3 citations.
- 2026-11-05 officer reports the mismatch; investigation and fix the same day.

## Why the dashboard missed it
The overall judge pass rate and field accuracy stayed high because only one loan type was affected and it
is a small share of volume. Stratified by loan type, agricultural equipment showed citation conflicts on 3
of 4 cases and a judge pass rate of 25%. The aggregate hid a localized regression, as it was built to.

## Root cause
A stale index. The prompt, the model and the code had not changed; the only change in the window before the
regression was the policy publication followed by the skipped index build on 2026-10-29
(`diagnosis.what_changed` on the change log). The AI-assisted explanation of the cause was confirmed against
the index build log and `PolicyIndex.is_stale()`, not accepted from code reading alone. The index does not
check freshness on load, so nothing failed: retrieval returned v3 chunks with full confidence.

## Fix and verification
Rebuilt the index from the current policy folder. Re-ran the SAME stratified check on the same cases:
citation conflicts for agricultural equipment went from 75% to 0%, and its judge pass rate from 25% to 75%
(the remaining failure, APP-009, is a known rubric gap unrelated to this incident). Other loan types were
unchanged.

## What changes so design catches it next time (not officer diligence)
- New escalation signal: `capstone.citation_conflicts` makes a citation of a different version of the rule
  applied fire the `conflicting_evidence` trigger automatically.
- The `policy-change` skill and the runbook make the index rebuild part of the same change as the policy
  publication, and require checking `is_stale()` afterwards.
- Monitoring: alert on a skipped or failed index build, and stratify the judge pass rate by loan type.
- Documentation: the runbook now says WHY the index must be rebuilt on every policy update.

## What we tell stakeholders
Plainly: for three days, explanations for agricultural equipment loans quoted an outdated coverage
threshold because a nightly job was skipped. Decisions used the correct threshold and no customer was
affected, but this was caught by an officer's diligence, not by our design. We have fixed it and added an
automatic check so a mismatch like this now escalates on its own.
