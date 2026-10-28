# Lab 2: Models, prompting and context engineering

Course: Chapter 2 (lessons 2.1 to 2.4) · Time: about 2.5 hours · Tests: 43 · Needs: Lab 1

By the end the system makes its first model calls: every call is routed to the tier your design chose,
intake returns validated structured data (and recovers from a bad first attempt), the lending rules run in
code, and the system prompt is cached.

```bash
pytest tests/test_lab2.py
python scripts/check.py 2
```

Read once: `atlas/fake_claude.py`'s docstring (what the offline model simulates) and `atlas/config.py`
(model IDs and prices live in one place).

---

## Lesson 2.1: Selecting the right Claude model

**The idea**
- Three axes: capability (ambiguity, multi-step reasoning, judgment), latency (time to first token and
  total, which matters when someone is waiting) and cost (price x volume).
- The rule: "the cheapest, fastest model that reliably clears the quality bar the task actually needs,
  verified rather than assumed". Choose per component. One tier for everything is the design error, in
  either direction: always the biggest wastes money; always the smallest fails quietly on judgment cases.
- Atlas: compact for intake (verified on messy scans), mid tier for the explanation, most capable for the
  low-volume, high-consequence investigator.

**Practical**
1. `selection.pick_tier()`: the hypothesis from a task profile (Lab 4 is the verification).
2. `llm.choose_model()`: look up `TASK_DESIGN[task]` from Lab 1 and map it to an API model ID. A task a
   person does (`decision`) must never get a model.

**Check:** `pytest tests/test_lab2.py -k test_2_1`

---

## Lesson 2.2: Deployment platforms and data residency

**The idea**
- Same models on three surfaces: the Anthropic API (new models and features first), Amazon Bedrock and
  Google Vertex AI (inside that cloud's identity, network and billing).
- The platform is an INHERITANCE decision: existing certifications, network boundaries and committed spend
  decide it, not developer taste. Atlas's core banking already runs in a regulator-reviewed AWS account,
  so Bedrock inherits that review.
- FedRAMP is a hard constraint: an unauthorized platform is not usable. But "most restrictive" is not
  automatically required when nothing forces it.
- Models reach marketplaces on different dates. Decide early what happens for a component whose tier is
  not there yet (wait, another tier, or a documented exception), never improvise at deployment.

**Practical:** `atlas/selection.py`: `choose_platform()` and `availability_exceptions()`.

**Check:** `pytest tests/test_lab2.py -k test_2_2`

---

## Lesson 2.3: System prompts, guardrails and prompting technique

**The idea**
- **Instruction hierarchy.** The system prompt holds what is stable (role, boundaries, output format,
  edge cases), so it can be reused and cached. The user message holds the per-request document. The tool
  schema holds structural constraints (enums, ranges, patterns). A system prompt that contains one
  applicant's ID is a template never separated from its variable content.
- **Technique per task.** Zero-shot for simple, well-specified tasks. Few-shot when the output is easier
  to show than describe; choose HARD boundary examples, not easy ones. Chain-of-thought when the
  reasoning is multi-step or is itself the deliverable (a regulator must follow why a rule flagged).
- **Guidance is not enforcement.** "Never approve a disbursement over $500,000 without a second reviewer"
  in a prompt is followed most of the time. If an occasional miss is unacceptable, check it in code at the
  point the action executes. That is why DSCR and LTV are arithmetic in `rules.py`, and why the schema
  rejects "180k".

**Practical** (in this order)
1. `prompting.TECHNIQUE` and `prompting.lint_system_prompt()`: a linter that flags per-request content
   and a missing edge-case section. It runs against every prompt in `prompts/`.
2. `schemas.LoanApplication`: add `Field(...)` constraints AND descriptions (the schema is part of the
   prompt). Notice what is not there: no SSN, no date of birth, no home address.
3. `extraction.application_tool()`, `validation_feedback()` and `extract()`: forced tool use, validate in
   code, send SPECIFIC feedback (field, value, rule) and retry; give up and hand the case to a person
   rather than guess.
4. `prompts/intake_v2.md`: turn it into a few-shot prompt. Read `data/applications/APP-004.txt` and
   `APP-010.txt`: a lease term next to the loan term, debts listed per month, revenue per month, EBITDA per
   quarter, years as a range, a blank purpose. Write rules plus at least two made-up worked examples (see
   the comment in the file). The small model gets these wrong, confidently, without examples.
5. `rules.compute_dscr()` and `rules.check_application()`: five rules, the referral bands, the New York
   CRE override, and a `policy_ref` on every result.

**Check:** `pytest tests/test_lab2.py -k test_2_3`

**Exam trap:** "add a line to the prompt telling the model never to exceed the limit" as the fix for an
unacceptable exposure.

---

## Lesson 2.4: Context windows, prompt caching and reuse

**The idea**
- The context window is a budget, not a wall: every token is paid on every call, times volume.
- Caching rewards a stable prefix. Put stable content first, in a consistent order, with a cache
  breakpoint; append what varies after it. A timestamp or request ID inside or before the stable block
  breaks the prefix on every call, with no error. The fix is reordering, not shrinking the document.
- Verify caching in practice (cache read tokens in the response), never assume it.
- Modular prompts: shared instruction modules written once and included everywhere (like Skills).
  One fix updates every component.

**Practical**
1. `llm.build_system(stable, dynamic)`: stable block with `cache_control`, dynamic block after it.
2. `llm.estimate_cost()`: input, cache writes (1.25x), cache reads (a fraction), output.
3. `prompting.compose()`: resolve `{{include: shared/x}}` recursively and detect cycles.
4. Watch the test `test_2_4_a_request_id_in_front_breaks_the_prefix_silently`: no error, three cache
   writes, triple the cost.

**Check:** `pytest tests/test_lab2.py -k test_2_4`

---

## See it work

```bash
python -c "from atlas import extraction, data_access; r = extraction.extract(data_access.load_application_text('APP-004')); print(r.attempts, r.errors); print(r.application)"
python -c "from atlas import extraction, data_access; print(extraction.extract(data_access.load_application_text('APP-004'), prompt_name='intake_v1').application.term_months)"
```

The second line uses the zero-shot prompt on the small model: 36 months, the lease term, reported with
confidence 0.9. That is why Lab 4 measures instead of trusting.

## Say it out loud

1. Why does intake run on the compact tier and the investigator on the most capable one? What would make
   you change intake's tier, and how would you know?
2. Atlas already has a reviewed AWS environment. Which platform, and why is that an inheritance decision?
   What do you do if the investigator's model isn't on that platform yet?
3. Where do these go: the output format, the applicant's document, "loan_type must be one of four
   values"? Why does it matter for caching?
4. When is few-shot the right technique, and what makes a good example?
5. Give one rule that may live in a prompt alone and one that must be enforced in code. What's the test?
6. A big policy manual is in every request but costs and latency didn't drop. What is the likely cause
   and the fix?
7. Your retry message says "please extract more accurately". Why does that fail, and what should it say?
