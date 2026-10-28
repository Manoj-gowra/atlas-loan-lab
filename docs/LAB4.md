# Lab 4: Evaluation, testing and optimization

Course: Chapter 4 (lessons 4.1 to 4.4) · Time: about 2 hours · Tests: 25 · Needs: Labs 1-3

By the end you can PROVE how the system performs: per category, on five axes, against the SLOs from Lab 1,
with an LLM judge you calibrated against human labels, and A/B tests that change one thing at a time.

```bash
pytest tests/test_lab4.py
python scripts/check.py 4
```

The golden set is `data/golden/golden.jsonl`: ten cases stratified as clean, messy, clear decline,
borderline and injection, with the expected fields, route and flags.

---

## Lesson 4.1: Defining evaluation metrics and test frameworks

**The idea**
- An evaluation is a built dataset with known answers, a defined metric per thing that matters, and a
  repeatable process. "If you can't rerun it on a changed system and get a comparable number, you have an
  opinion about a demo."
- Five axes, each can fail alone: accuracy, latency (a distribution: look at the slow tail), cost
  (measured, not assumed), SAFETY (harmful or biased output) and SECURITY (do the boundaries hold?).
- Mixed methods: exact match where there is one right answer (intake fields), an LLM judge for open text
  (explanations) with clear, specific, OBSERVABLE criteria, and human review to CALIBRATE the judge.
- Stratify the dataset deliberately; the per-category breakdown is the primary result and the aggregate
  is a summary. A dataset that accumulates rather than represents leaves rare categories too thin.

**Practical**
1. `evals.score_case()`: one golden row, five axes.
2. `evals.summarize()`, `check_slos()`, `weak_strata()` and `thin_strata()`.
3. `judge.CRITERIA`: start with three observable criteria (flagged rules named, their sections cited, no
   approve/decline language) and implement `judge_explanation()` and `agreement()`.
4. Calibrate: compute agreement with `data/golden/judge_labels.jsonl`. One case disagrees. Read the
   human's note, add the criterion they care about, and re-measure until agreement is 1.0.

**Check:** `pytest tests/test_lab4.py -k test_4_1`

**Exam trap:** using an LLM judge for intake fields, where exact match works and costs nothing.

---

## Lesson 4.2: A/B testing and iterative improvement

**The idea**
- Isolate ONE variable. Change the prompt and the model together and you learn nothing about either.
- Enough data: a modest difference on five cases can be ordinary variance. Stratify the comparison set
  like the eval set. (The offline model is deterministic, so variance is zero here; real Claude is not.)
- Specific feedback beats "be more accurate" (you built it in Lab 2's `validation_feedback`).
- Close the loop: a fix is a hypothesis until you re-run the SAME dataset, see the weak category recover
  and confirm nothing else regressed.

**Practical**
1. `experiments.differing_variables()`, `assert_single_variable()` and `undersized_strata()`.
2. `feedback.FeedbackStore.to_golden_rows()`: officer corrections become regression cases.
3. Read the two A/B tests in `tests/test_lab4.py`: few-shot vs zero-shot on the small model (prompt fix),
   then zero-shot on the small vs a bigger model (model upgrade). Which is cheaper for the same accuracy?

**Check:** `pytest tests/test_lab4.py -k test_4_2`

---

## Lesson 4.3: Diagnosing system failures

**The idea**
- A wrong output is a symptom with three possible causes and three different fixes. Info NOT in context:
  a hallucination, fixed by grounding/retrieval (not "don't make things up"). Info present but the
  instruction unclear: a prompt failure, fixed by a targeted correction. Info present, instruction clear,
  still fails reliably: a model mismatch, fixed by a more capable tier.
- Start with "what changed right before the regression?" Correlate timing with deployments, configuration
  and document refreshes before guessing.
- Structural validation (schema) and semantic validation (is it plausible?) are separate checks.

**Practical:** `atlas/diagnosis.py`: `diagnose()`, `semantic_checks()` (now part of the pipeline) and
`what_changed()` (you use it again in Labs 7 and 8).

**Check:** `pytest tests/test_lab4.py -k test_4_3`

---

## Lesson 4.4: Optimizing cost, latency and performance

**The idea**
- Optimization comes AFTER correctness: a wrong answer faster and cheaper is not an improvement. Re-verify
  every optimization on the same eval set.
- Read the same traces for WASTE: cache misses on a stable prefix, retrieval pulling 8 chunks when answers
  cite 1 or 2, a tier a stratum doesn't need. Three levels: token, call, architecture.
- Batch vs synchronous is "is anyone waiting in real time?" vs "is it done by a deadline?". Nightly
  screening due before the morning shift is a batch job at half the price.

**Practical:** `atlas/optimize.py`: `find_waste()`, `processing_plan()` and `accept_optimization()`.

**Check:** `pytest tests/test_lab4.py -k test_4_4`

---

## See it work

```bash
python scripts/run_evals.py
```

Read `runs/eval_report.md`. In comparison A, the zero-shot prompt still passes the OVERALL field accuracy
target while the messy category collapses: exactly the aggregate-hides-the-stratum lesson. Comparison B
shows the bigger model also fixes it, at a higher cost per application. Then read the executive summary at
the bottom: that is Lab 6's job, previewed.

## Say it out loud

1. Name the five evaluation axes and give an Atlas metric for each.
2. Why exact match for intake fields but a judge for explanations? What calibrates the judge?
3. Your judge agrees with humans 80% of the time. What do you do?
4. Someone changed the prompt and the model in one release and accuracy rose. What did you learn?
5. The policy check started citing an old threshold right after a scheduled document refresh; no code,
   prompt or model changed. Where do you look first?
6. Retrieval returns 8 chunks and answers cite 2. What do you test, and what must stay true?
7. When is batch the right answer, and when is it wrong?
