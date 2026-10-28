"""Scoreboard for the eight labs (one per course chapter).

    python scripts/check.py              # all labs, one line each
    python scripts/check.py 3            # lab 3 only, with failure details
    python scripts/check.py all --solution   # the reference solution (all green)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABS = {
    1: "Ch1 Solution design and architecture",
    2: "Ch2 Models, prompting and context engineering",
    3: "Ch3 Integration",
    4: "Ch4 Evaluation, testing and optimization",
    5: "Ch5 Governance, safety and risk",
    6: "Ch6 Stakeholder communication and lifecycle",
    7: "Ch7 Developer productivity and enablement",
    8: "Ch8 Capstone: cross-domain scenario",
}


def run(lab: int, solution: bool, verbose: bool) -> tuple[int, int, int, str]:
    cmd = [sys.executable, "-m", "pytest", f"tests/test_lab{lab}.py", "-p", "no:cacheprovider",
           "--tb=short" if verbose else "--tb=no", "-rfE" if verbose else "-rN"]
    if solution:
        cmd.append("--solution")
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout
    summary = next((line for line in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", line)), "")
    count = lambda word: sum(int(n) for n in re.findall(rf"(\d+) {word}", summary))
    return count("passed"), count("failed") + count("error"), count("skipped"), out


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    solution = "--solution" in sys.argv
    labs = list(LABS) if not args or args[0] == "all" else [int(args[0])]
    verbose = len(labs) == 1
    print(f"Atlas Loan Lab - {'REFERENCE SOLUTION' if solution else 'your code'}\n")
    total_pass = total = 0
    for lab in labs:
        passed, failed, skipped, out = run(lab, solution, verbose)
        n = passed + failed
        total_pass, total = total_pass + passed, total + n
        status = "DONE" if n and not failed else "in progress" if passed else "not started"
        extra = f", {skipped} skipped" if skipped else ""
        print(f"Lab {lab}  {LABS[lab]:<48} {passed:>3}/{n:<3} {status}{extra}")
        if verbose and failed:
            print("\n" + out)
    if len(labs) > 1:
        print(f"\nTotal: {total_pass}/{total} tests passing")


if __name__ == "__main__":
    main()
