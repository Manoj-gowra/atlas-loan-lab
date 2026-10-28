"""The team's reusable workflow (lesson 7.1): run the tests, summarize failures BY LAB, same format every time.

    python scripts/test_summary.py [--solution]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solutions" if "--solution" in sys.argv else ROOT))

from atlas.devtools import summarize_failures  # noqa: E402

cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--tb=no", "-rfE"]
if "--solution" in sys.argv:
    cmd.append("--solution")
out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout
try:
    failures = summarize_failures(out)
except NotImplementedError:  # before Lab 7: a plain list instead of the grouped view
    print("(implement atlas/devtools.py summarize_failures in Lab 7 for the grouped view)")
    failures = {"all": [line.split("::", 1)[-1].split(" - ")[0] for line in out.splitlines()
                        if line.startswith(("FAILED", "ERROR"))]} if "FAILED" in out or "ERROR" in out else {}
if not failures:
    print("All tests pass.")
for lab, tests in failures.items():
    print(f"{lab}: {len(tests)} failing" + (f" -> reread docs/LAB{lab[3:]}.md" if lab.startswith("lab") else ""))
    for name in tests:
        print(f"    {name}")
