# Lab 1: Solution design and architecture

Course: "What This Exam Tests" + Chapter 1 (lessons 1.1 to 1.4) · Time: about 1.5 hours · Tests: 33

By the end you will have turned Atlas's vague mandate into a decomposition, a value number, measurable
targets, a pattern and tier per task, the coordinator's handoff and synthesis rules, and a feedback record.
No model calls yet: this lab is pure design, written as code so the rest of the system can use it.

**Before you start:** read `docs/discovery_notes.md` (the workshop notes) and `docs/ARCHITECTURE.md`.

```bash
pytest tests/test_lab1.py            # your progress
python scripts/check.py 1            # same, with failure details
```

---

## Lesson 0: What This Exam Tests

**The idea**
- The exam tests judgment under constraints. Wrong answers are real techniques, wrong for this situation.
- Three distractors come back again and again. "Add logging" is a detective control: you learn after the
  fact. "Add a confirmation prompt" is a compensating control: the capability is still wired up. "Use a
  bigger model" is not a control: it confuses following instructions with being authorized.
- When the question says "best reduces risk", look for the preventive control. It removes the root cause.

**Practical:** `atlas/controls.py`
1. `classify_control(option)`: lower-case the option, then check the word lists in order: not a control,
   preventive, detective, compensating. Nothing matched means `"unknown"`.
2. `best_risk_reduction(options)`: the first preventive option, or `ValueError`.

**Check:** `pytest tests/test_lab1.py -k test_0`

**Exam trap:** "Use a more capable model that will restrict itself" sounds preventive. It isn't a control.

---

## Lesson 1.1: From business problem to solution architecture

**The idea**
- The mandate is "help our loan officers process applications faster so we can handle more volume
  without hiring". Don't start with a solution. Ask four questions: (1) which distinct tasks are hidden in
  it, (2) the input and output of each, (3) the risk and reversibility of each output, (4) which tasks
  actually move the business metric.
- The answer for Atlas: automate intake and the policy check, assist with the memo draft, keep the
  decision human. A decline can be an unlawful adverse action if it is wrong.
- Tie the design to value: 90 minutes x 4,000 applications x two-thirds removed is about 4,000
  officer-hours a year. That number is the budget ceiling and the yardstick for later trade-offs.
- Turn "fast" and "accurate" into numbers you can test (SLOs). They become what Lab 4 checks.

**Practical:** `atlas/design.py`
1. `DECOMPOSITION`: four `Task` rows (intake, policy_check, drafting, decision), with input, output, risk,
   reversibility, whether each moves the metric, and the disposition (automate / assist / human).
2. `officer_hours_saved()` and `max_cost_per_application()`: two lines of arithmetic each.
3. `SLOS`: every value from Sam and Priya's quotes in the discovery notes (percentages as 0-1).

**Check:** `pytest tests/test_lab1.py -k test_1_1`

**Exam trap:** automating the impressive task (the decision) rather than the valuable one (intake).

---

## Lesson 1.2: Choosing the architecture pattern

**The idea**
- Three patterns on an autonomy spectrum. An **augmented LLM** is one bounded call plus retrieval, tools
  or memory. A **workflow** is a predefined path (chaining, routing, parallelization). An **agent**
  decides its next step at runtime. Each step up costs predictability, money and auditability.
- Stop at the first yes: (1) can it be one bounded call? (2) can you draw the whole flowchart in
  advance? (3) only if the path depends on runtime results you can't enumerate, use an agent, with a
  bounded loop and a stop condition in code.
- Choose per task, not for the whole system. Routing among known options is still a workflow.
- Atlas: intake = augmented LLM, policy check = workflow, drafting = workflow, decision = human. Only the
  optional "investigate this borderline case" capability is an agent.

**Practical:** `atlas/design.py`
1. `choose_pattern()`: three `if`s in order.
2. `TASK_DESIGN`: one `TaskDesign(pattern, model, why)` per task. The `why` is the sentence you would say
   in an interview. `llm.choose_model()` reads this table in Lab 2, so your design really drives routing.

**Check:** `pytest tests/test_lab1.py -k test_1_2`

**Exam trap:** "it should be an agent because it's AI". Agent-first is the anti-pattern.

---

## Lesson 1.3: Multi-agent systems and orchestration strategy

**The idea**
- Multi-agent is one more step up the spectrum. Only three signals justify it: independent subtasks that
  can run in parallel, too many tools for one agent (selection errors rise past about 5), and context
  pollution from exploring many angles in one session.
- A **coordinator** decomposes, dispatches and synthesizes; it never investigates itself. A
  **specialist** has one bounded scope, its own small toolset and a scoped brief (not the whole case). It
  returns a structured result, and its session is disposable.
- **Provenance** is the most tested failure. Every finding carries which specialist produced it, whether
  it was in scope, its confidence and what it could not check. The coordinator attributes each claim and
  labels out-of-scope asides as unverified instead of folding them into the conclusion. The fix is
  attribution, not a second validation pass or a better prompt.

**Practical**
1. `design.needs_coordinator()`: any of the three signals (more than 5 tools counts).
2. `coordination.BRIEF_FIELDS`: for each specialist, only the case facts it needs. The financial-ratio
   specialist must get what it needs to recompute DSCR, or it will report "unable to check" (the fake
   model really behaves like that in Lab 3).
3. `coordination.specialist_brief()`: filter the facts, keep the order, format.
4. `coordination.synthesize()`: provenance from the code that ran the specialist (ignore what the text
   claims), asides separated, unable-to-check prefixed, then the recommendation rule in the docstring.

**Check:** `pytest tests/test_lab1.py -k test_1_3`

**Exam trap:** a coordinator that "also checks the bureau itself to save a call". It mixes roles.

---

## Lesson 1.4: Reference architectures and feedback loops

**The idea**
- Every architecture has four stages: input, processing, output, feedback. Skipping the feedback loop is
  the most common gap.
- Six reference architectures: augmented LLM, RAG assistant, fixed workflow, agentic investigator,
  coordinator + specialists, and the human-in-the-loop review gate. The review gate is a checkpoint after
  processing and before the action takes effect, not a processing pattern.
- A feedback loop records the system's ORIGINAL output, the CORRECTED value and the context (which field,
  step and component). "We log everything" is not a feedback loop. These pairs feed the eval set (Lab 4)
  and drift alerts (Lab 3).

**Practical**
1. `design.reference_architecture()`: an if-chain, most specific signal first.
2. `feedback.FeedbackStore.record()`: refuse half a pair, append one JSON line.

**Check:** `pytest tests/test_lab1.py -k test_1_4`

---

## See it work

Open `atlas/pipeline.py` (given) and find each box of your decomposition and the four stages. Then:

```bash
python scripts/demo.py --solution --app APP-006
```

That is where you are heading: intake, rules, a cited explanation, three specialists with attributed
findings, an unverified aside, a memo and an approval packet.

## Say it out loud

Answer without looking, then check the docstrings.

1. Which of these best reduces the risk of an intake agent changing loan statuses: logging, a confirmation
   prompt, a bigger model, or removing the tool? Why are the others wrong?
2. Name the four decomposition questions and apply them to "draft the credit memo".
3. Why is the policy check a workflow even though it "decides" between pass, borderline and fail?
4. What are the three signals for multi-agent? Which ones does the Atlas investigator show?
5. A specialist mentions a possible affiliate business while checking cash flow. What does the
   coordinator do with it?
6. What three things must a feedback record capture, and what is it used for later?
7. Where does a human-in-the-loop review gate sit, and why there?
