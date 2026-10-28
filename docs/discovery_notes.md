# Discovery workshop notes: Atlas Financial commercial lending assistant

**Date:** 2026-09-08 · **Facilitator:** you (solution architect) · **Format:** three short sessions

You use these notes in Lab 1 (value and targets: `design.py`) and Lab 6 (need, requirements and
constraints: `requirements.py`). Turn what people *said* into numbers, checkable requirements and
constraints you have tested.

## Who was in the room

| Person | Role | Cares about |
|---|---|---|
| Daniel Reyes | Head of Commercial Lending (sponsor) | Volume per officer, no new hires |
| Sam Ortiz | Senior Loan Officer (end user) | Trustworthy case files, less retyping |
| Raj Patel | Chief Compliance Officer | Fair lending, adverse action, audit, data |
| Lena Brooks | Head of Cloud Platform | Where it runs, integration, security review |
| Priya Shah | Finance business partner | Running cost |
| Grace Okonkwo | Credit Committee chair | What reaches the committee |

## Session 1: the stated want

**Daniel:** "Help our loan officers process applications faster so we can handle more volume without
hiring. I want an AI that reads loan documents."

## Session 2: testing the need underneath it

You asked: *What happens today without this? What does success look like in six months? Who is hurt by
the current state, and how?*

**Sam:** "We take about 4,000 applications a year. Each one costs an officer about 90 minutes of
retyping figures from statements and tax returns and hunting through the 200-page policy manual.
Most of them are standard cases. The borderline ones - the ones that actually need judgment - get
squeezed because we're buried in routine paperwork."

**Daniel:** "If we can take two-thirds of that manual time out, that's real capacity. Use $85 an hour
as the loaded cost of an officer's time."

**Sam:** "I need the case file ready within a minute for 95% of applications - I upload and come back
to it. If the figures are wrong even occasionally I'll stop trusting it: field accuracy has to be at
least 95%, and that has to hold for every document type, not just on average. Routing - approve-looking,
decline-looking, needs investigation - has to be right at least 9 times out of 10. If more than 30% of
files need me to check fields, we've gained nothing."

**Priya:** "Budget for model usage is 5 cents per application on average. Hard cases can cost more
as long as the average holds."

**Grace:** "Anything over an officer's lending authority still comes to my committee, with the evidence
attached. A flag with no evidence is useless to us."

## Session 3: constraints, and which ones are really fixed

You asked each owner: *What happens if this limit cannot be met?*

| Statement | Owner | Answer to "what happens if it can't be met?" |
|---|---|---|
| "It must integrate with our current loan-origination platform." | Lena | "Then we'd have to revisit the whole approach - replacing the LOS is a multi-year programme nobody will fund." |
| "Applicant data must stay inside our AWS account." | Lena | "We cannot do it. That is how we passed the regulator's cloud review." |
| "A person makes every credit decision." | Raj | "We cannot. Policy 3.1 and fair-lending law." |
| "Results should show up in the Lending Hub dashboard." | Daniel | "I'd prefer it, but officers would be fine with an equivalent view." |
| "The team would like it built in Python." | Lena | "Nice to have; we could work around it." |

**Raj:** "Guarantors' SSNs, dates of birth and home addresses never go to the model or into logs.
Age, marital status and the other prohibited factors never appear in a memo. Every decision goes into a
tamper-evident audit log. Decline reasons must cite the specific policy section."

## Follow-ups you should have asked (practice)

- What happens to applications the system cannot read at all? (Answer: an officer handles them as today.)
- Who owns policy documents and how are new versions published? (Credit Risk Committee; a new version is
  effective from a date; older applications keep their version.)
- How do we roll back if accuracy drops after launch?
