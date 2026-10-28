---
name: run-evals
description: Run the Atlas evaluation suite and the A/B comparisons, then report results against the business targets in plain English. Use before merging any change to prompts, models, retrieval or the pipeline.
---

# Run evals

1. Run `python scripts/run_evals.py`. It writes `runs/eval_report.md`.
2. Report the overall numbers AND every stratum (document type, loan type) below target. An average can
   hide the weak group, so always read the breakdown.
3. If the user is comparing a change, confirm only ONE variable differs, then show the comparison and
   say which variant wins on accuracy, cost and speed, and what the trade-off is.
4. Finish with the executive summary lines from the report, ready to paste to stakeholders.
