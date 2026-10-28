# Lab 5: Governance, safety and risk

Course: Chapter 5 (lessons 5.1 to 5.3) · Time: about 2 hours · Tests: 37 · Needs: Labs 1-4

Until now the guardrails and escalation were pass-throughs so the pipeline could run. Here you make them
real: screening on the way in and out, failing secure, four escalation triggers with queues and evidence,
dollar-limited human approval, a tamper-evident audit log and a fairness check.

```bash
pytest tests/test_lab5.py
python scripts/check.py 5
```

---

## Lesson 5.1: Guardrails, safety controls and failure modes

**The idea**
- A guardrail is a control enforced independently of the model, at a specific point. Three points, used
  together: INPUT screening (injection, sensitive data that shouldn't enter context), OUTPUT screening
  (policy violations, leaks) and TOOL-CALL authorization (the gate from Lab 3). "Behave safely" in a
  system prompt is guidance.
- FAIL SECURE: when a guardrail itself fails (outage, timeout, ambiguous result), block or hold. An outage
  in the authorization path is not evidence the action is safe.
- Direct injection arrives in the user's request. INDIRECT injection arrives in content the system reads
  (an uploaded document): the attacker is whoever wrote the document. Defence: treat it as untrusted data,
  delimit and label it, screen it, and keep the component that reads it away from privileged tools
  (privilege separation; intake has no data tools).
- Risks and their primary defence: hallucination -> grounding and citation checks; injection -> untrusted
  data + independent authorization; jailbreak -> output screening + instruction hierarchy; unbounded
  delegation -> least privilege; data leakage -> per-caller scoping where content is returned.

**Practical:** `atlas/guardrails.py`
1. `redact_pii()`: SSN, date of birth, home address, email, phone, before the model and before the logs.
2. `screen_document()`: replace injected lines and flag the case. No false positives on the nine clean
   documents.
3. `fail_secure()`: a screening check that raises holds the case.
4. `find_prohibited_factors()` and `screen_output()`: age, marital status and the other prohibited
   factors (General Lending Standards 1.1), plus leaked SSNs or system-prompt text.

Read `data/applications/APP-008.txt` PART 4 to see the injection. Without your screening, the offline
model obeys it (watch the memo).

**Check:** `pytest tests/test_lab5.py -k test_5_1`

---

## Lesson 5.2: Human-in-the-loop and escalation design

**The idea**
- Escalation is a deliberate design for CATEGORIES of decisions, not a net for "the model feels unsure".
  A guardrail stops what must never happen; escalation routes what may be right but belongs to a person.
- Four triggers: HIGH IMPACT (irreversible or high stakes: a decline, a loan above the officer's
  authority) regardless of confidence; POLICY GAP (no written rule covers it; the closest rule is a guess);
  CONFLICTING EVIDENCE (stated vs verified figures; specialists pulling opposite ways; never pick or
  average); LOW CONFIDENCE (uncertain fields, an escalated investigation, a tampered document).
- Every escalation carries an APPROVAL PACKET: the action requested, the evidence and where each piece
  came from, which triggers fired, and the system's recommendation and reasoning. A bare "case waiting"
  link fails.
- Calibrate the volume: too many escalations -> reviewer fatigue -> rubber-stamping.

**Practical:** `atlas/escalation.py`: `low_confidence_fields()`, `escalation_triggers()`, `QUEUES`,
`build_approval_packet()`, `route_to_queues()` and `rubber_stamp_risk()`.

**Check:** `pytest tests/test_lab5.py -k test_5_2`

---

## Lesson 5.3: Compliance and ethical AI in practice

**The idea**
- Compliance constrains the architecture from the FIRST decision (platform, data flow, logging), not at a
  final legal review. GDPR: data subject rights and limits on automated decisions with significant effects
  (meaningful human involvement). HIPAA: a vendor agreement (BAA), an audit trail of who accessed what and
  when, minimum necessary access. FedRAMP: which deployment platforms are usable at all.
- A platform's authorization doesn't cover your application's logging, scoping and data flow.
- Fairness is a separate obligation: a fully compliant system can still be biased. Stratify outcomes by
  group, watch PROXIES (ZIP codes, home addresses) and explain decisions with their policy reasons.

**Practical**
1. `approval.AuditLog.append()` and `verify()`: each entry hashes the previous one, so editing history is
   detectable.
2. `approval.ApprovalGate.finalize()`: a person decides, within their dollar authority (loan officer up to
   $500,000, senior credit officer up to $2,000,000, the committee above). Overrides need a reason.
   This is lesson 2.3's "$500,000 second reviewer" rule, enforced instead of requested.
3. `compliance.REGIMES`, `regimes_constraining()`, `approval_rates()`, `adverse_impact_ratio()` and
   `proxy_leaks()`.

**Check:** `pytest tests/test_lab5.py -k test_5_3`

---

## See it work

```bash
python scripts/demo.py                    # triggers and flags for all ten cases
python scripts/demo.py --app APP-008      # the injection, contained
python scripts/demo.py --app APP-003      # $2.4M: who may sign it?
python -c "from atlas import authz; authz.AUTHZ.outage = True; from atlas.pipeline import process_application as p; c = p('APP-006'); print(c.investigation.unable_to_check, c.recommendation)"
```

## Say it out loud

1. Name the three guardrail points. Which one stops an injected instruction in an uploaded document from
   turning into a status change, even if screening misses it?
2. The screening service times out. What happens to the case, and why not let it through?
3. What makes APP-008's attack INDIRECT, and what is privilege separation?
4. Name the four escalation triggers with an Atlas example of each.
5. What goes into an approval packet, and why is a link to the case not enough?
6. How would you notice reviewers are rubber-stamping?
7. Which regime constrains automated decisions, which the audit trail, which the platform?
8. Approval rates are 80% for one group and 60% for another. What does the 0.75 ratio tell you, and what
   doesn't it tell you?
