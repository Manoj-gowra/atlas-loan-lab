---
name: test-summary
description: Run the Atlas test suite and summarize failures grouped by lab, in the same format every time. Use when someone asks what is failing, before committing, or after pulling changes.
---

# Test summary

1. Run `python scripts/test_summary.py` (add `--solution` to check the reference implementation).
2. Present the result as a table: lab, number of failing tests, the failing test names.
3. For each failing lab, name the lab guide section to reread (`docs/LAB<n>.md`).
4. Do not change code unless the user asks; this workflow reports, it does not fix.
