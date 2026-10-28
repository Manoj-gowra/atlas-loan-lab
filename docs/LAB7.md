# Lab 7: Developer productivity and enablement

Course: Chapter 7 (lessons 7.1 and 7.2) · Time: about 1 hour · Tests: 9 · Needs: Labs 1-6

You configure Claude Code for the whole team, the way the course recommends, and you practise using an
assistant to FORM a debugging hypothesis and the traces to CONFIRM it. If you have Claude Code installed,
open this folder in it as you go: everything you configure here takes effect.

```bash
pytest tests/test_lab7.py
python scripts/check.py 7
```

---

## Lesson 7.1: Configuring Claude tooling for teams

**The idea**
- Without team configuration, risk and quality depend on whoever is at the keyboard: one engineer runs it
  wide open, another has it disabled, a third uses different conventions. That is worse than any
  consistent choice.
- Three layers. CHECKED-IN CONFIGURATION (project memory: conventions, how tests run, which directories
  are GENERATED output) is guidance. The PERMISSION POLICY (what the assistant may do without asking)
  backs it up. REUSABLE WORKFLOWS package a repeated team task once (Skills).
- Least privilege for the assistant itself: read and edit application code freely, but pushing to the
  deploy branch or editing compliance-relevant files needs explicit confirmation EVERY time. New engineers
  inherit a tested default instead of discovering one.
- Checked-in instructions are guidance; hooks and permission rules are enforcement.

**Practical**
1. `CLAUDE.md`: replace the TODO with the project memory (commands, layout with `runs/` marked as
   generated, the rules). Under ~40 lines.
2. `.claude/settings.json`: `permissions.allow` (running tests, editing `atlas/`, `prompts/`, `docs/`),
   `permissions.ask` (`Bash(git push *)`, editing `data/policies/**` and `atlas/rules.py`), `permissions.deny`
   (reading `.env` and `data/.fake/`). Then `hooks`: a `PreToolUse` hook on `Edit|Write` that runs
   `scripts/hooks/protect_files.py` (exit code 2 blocks the edit) and a `PostToolUse` hook that runs
   `scripts/hooks/check_syntax.py`. Command form: `python3 "$CLAUDE_PROJECT_DIR/scripts/hooks/<file>.py"`.
3. `.claude/skills/test-summary/SKILL.md` and `.claude/skills/policy-change/SKILL.md`: frontmatter with a
   `name` and a `description` that says WHAT and WHEN (Claude chooses skills by it), then the procedure.
   `run-evals` is a finished example.
4. `atlas/devtools.py` `summarize_failures()`: the engine behind the test-summary workflow.

**Check:** `pytest tests/test_lab7.py -k test_7_1`

**Try it:** in Claude Code, ask it to edit `runs/review_queue.jsonl` (the hook blocks it), then ask
"what's failing?" (it should pick the test-summary skill).

---

## Lesson 7.2: AI-assisted workflows and operational debugging

**The idea**
- An assistant speeds up FORMING a hypothesis (tracing logic across files, correlating an error with
  code), not CONFIRMING it. A confident root cause from code alone is a plausible guess.
- Code answers "what could cause this"; logs and traces answer "what did happen" and "is the proposed
  cause right". So give the debugging assistant SCOPED, READ-ONLY access to the traces, deployment history
  and change logs an investigation needs, not broad production access "for thoroughness".
- Apply the diagnostic framework: what changed right before? (a deployment, a configuration change, a
  document refresh).

**Practical**
1. `devtools.verify_hypothesis()`: check each piece of evidence a claim rests on against the trace.
2. `atlas/ops_mcp.py` `build_server()`: register `list_traces`, `get_trace` and `get_change_log`, all
   read-only, and nothing else. `.mcp.json` already registers it as `atlas-ops`.

**Check:** `pytest tests/test_lab7.py -k test_7_2`

**Try it:** in Claude Code, ask "why did APP-006's bank statement check take two calls?" after running
`python scripts/demo.py --app APP-006`. It should answer from `get_trace`, not from reading the code.

---

## Say it out loud

1. What goes in checked-in configuration vs the permission policy vs a skill? Which of them is enforcement?
2. Which actions should always require confirmation in Atlas, and why those?
3. A teammate wants `Bash(*)` in `allow` "to save clicks". Your answer?
4. Claude Code says "the null comes from `rules_for` not handling CA agricultural loans". How do you
   confirm or reject that before changing code?
5. Why read-only traces and the change log, rather than production database access?
