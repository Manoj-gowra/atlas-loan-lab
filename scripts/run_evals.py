"""Evaluation report with two single-variable A/B comparisons. Writes runs/eval_report.md.

    python scripts/run_evals.py [--solution]

A: prompt  - few-shot (intake_v2) vs zero-shot (intake_v1), both on the small model
B: model   - zero-shot on the small model vs zero-shot on a bigger model
Is a prompt fix cheaper than a model upgrade? Read accuracy AND cost, per category.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solutions" if "--solution" in sys.argv else ROOT))

from atlas import communication, config, data_access, llm  # noqa: E402
from atlas.design import SLOS  # noqa: E402
from atlas.evals import compare, run_eval, summarize, weak_strata  # noqa: E402
from atlas.experiments import run_ab  # noqa: E402


def evaluate(**kwargs):
    llm.reset_client()
    data_access.reset_simulations()
    return summarize(run_eval(**kwargs))


def main() -> None:
    small = config.MODELS["haiku"]
    ab_prompt = run_ab({"prompt_name": "intake_v2", "intake_model": small}, {"prompt_name": "intake_v1", "intake_model": small}, evaluate)
    ab_model = run_ab({"prompt_name": "intake_v1", "intake_model": small},
                      {"prompt_name": "intake_v1", "intake_model": config.MODELS["sonnet"]}, evaluate)
    current = ab_prompt["a"]
    report = [
        "# Atlas evaluation report", "", f"Mode: {config.mode()} | golden cases: {current['overall']['n']}", "",
        f"## A. Variable under test: {ab_prompt['variable']} (v2 few-shot vs v1 zero-shot)", "```",
        compare("v2 few-shot", ab_prompt["a"], "v1 zero-shot", ab_prompt["b"]), "```",
        f"Weak strata with v1: {weak_strata(ab_prompt['b'], SLOS) or 'none'}", "",
        f"## B. Variable under test: {ab_model['variable']} (zero-shot on small vs bigger model)", "```",
        compare("v1 + haiku", ab_model["a"], "v1 + sonnet", ab_model["b"]), "```", "",
        "## Status for the business (current configuration)", "",
        communication.summarize_for("executive", current, SLOS, weak_strata(current, SLOS)), "",
        "## Status for engineering", "```",
        communication.summarize_for("technical", current, SLOS, weak_strata(current, SLOS)), "```",
    ]
    text = "\n".join(report)
    print(text)
    config.RUNS.mkdir(parents=True, exist_ok=True)
    (config.RUNS / "eval_report.md").write_text(text + "\n")
    print(f"\nSaved to {config.RUNS / 'eval_report.md'}")


if __name__ == "__main__":
    main()
