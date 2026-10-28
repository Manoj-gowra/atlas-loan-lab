"""Run the lab tests and write per-lesson progress for the lab UI.

    python site/progress.py                  # all labs  -> .atlas/progress.json
    python site/progress.py --lab 3          # one lab, merged into the existing file
    python site/progress.py --solution       # grade the reference solution instead
    python site/progress.py --print          # also print a short scoreboard

The browser UI (site/serve.py) watches .atlas/progress.json, so any run keeps it current.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labmodel  # noqa: E402

ROOT = labmodel.ROOT
STATE = ROOT / ".atlas" / "progress.json"


OUTPUT_LIMIT = 12000  # characters of pytest output kept per lab for the UI
WHERE_RE = re.compile(r'File "(?:[^"]*/)?((?:atlas|prompts|tests|scripts)/[^"]+)", line (\d+)')


def diagnose(code: int, output: str, have_results: bool) -> str:
    """One plain-English line when pytest could not grade the lab (as opposed to tests simply failing)."""
    if "No module named pytest" in output:
        return f"pytest is not installed for {sys.executable}. Activate .venv and run: pip install -r requirements.txt"
    if have_results and code in (0, 1):  # 1 just means some tests failed, which is the normal state of a lab
        return ""
    lines = [l for l in output.splitlines() if l.strip()]
    spots = [m for l in lines if (m := WHERE_RE.search(l))]
    error = next((l[1:].strip() for l in reversed(lines) if re.match(r"^E\s+\w*(Error|Exception)\b", l)), "")
    if error:
        return f"{error} in {spots[-1].group(1)}:{spots[-1].group(2)}" if spots else error
    return lines[-1].strip("= ") if lines else f"pytest exited with code {code} and printed nothing"


def run_lab(n: int, solution: bool = False) -> tuple[list[dict], str, str]:
    """Run one lab's tests. Returns (one record per test, pytest output, setup error or "")."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "r.xml"
        cmd = [sys.executable, "-m", "pytest", f"tests/test_lab{n}.py", "-p", "no:cacheprovider",
               "-q", "--tb=short", f"--junitxml={xml}"]
        if solution:
            cmd.append("--solution")
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return [], "", f"The Lab {n} tests ran for more than 5 minutes and were stopped. Look for an infinite loop."
        output = (proc.stdout + proc.stderr)[-OUTPUT_LIMIT:]
        if not xml.exists():
            return [], output, diagnose(proc.returncode, output, False)
        results = []
        for case in ET.parse(xml).iter("testcase"):
            bad = case.find("failure")
            if bad is None:
                bad = case.find("error")
            skipped = case.find("skipped") is not None
            results.append({
                "name": case.get("name"),
                "ok": bad is None and not skipped,
                "skipped": skipped,
                "message": (bad.get("message") or "").strip().splitlines()[0][:300] if bad is not None and (bad.get("message") or "").strip() else "",
                "detail": (bad.text or "").strip()[-1400:] if bad is not None else "",
            })
        error = diagnose(proc.returncode, output, bool(results))
        # A collection error (say a syntax error in atlas/) stops pytest before any real test runs.
        return ([] if error else results), output, error


def summarize(lab: dict, tests: list[dict], output: str = "", error: str = "") -> dict:
    ids = [l["id"] for l in lab["lessons"]]
    lessons = {i: {"passed": 0, "failed": 0, "total": 0, "failures": []} for i in ids}
    for t in tests:
        if t["skipped"]:
            continue
        lid = labmodel.lesson_for_test(lab["n"], t["name"], ids)
        entry = lessons[lid]
        entry["total"] += 1
        if t["ok"]:
            entry["passed"] += 1
        else:
            entry["failed"] += 1
            entry["failures"].append({"name": t["name"], "message": t["message"], "detail": t["detail"]})
    for e in lessons.values():
        e["failures"] = e["failures"][:5]
        e["status"] = "done" if e["total"] and not e["failed"] else "progress" if e["passed"] else "todo"
    passed = sum(e["passed"] for e in lessons.values())
    total = sum(e["total"] for e in lessons.values())
    status = "done" if total and passed == total else "progress" if passed else "todo"
    return {"passed": passed, "total": total, "status": status, "lessons": lessons,
            "output": output, "error": error, "ranAt": time.time()}


def add_unlocks(model: dict, labs: dict) -> dict:
    """Soft gating: a lesson is 'unlocked' when every earlier lesson (and lab) is done. Mark the next one to do."""
    nxt = None
    prior_done = True
    for lab in model["labs"]:
        info = labs.get(str(lab["n"]))
        if not info:
            continue
        info["unlocked"] = prior_done
        lesson_ok = prior_done
        for l in lab["lessons"]:
            e = info["lessons"][l["id"]]
            e["unlocked"] = lesson_ok
            if lesson_ok and e["status"] != "done" and nxt is None:
                nxt = {"lab": lab["n"], "lesson": l["id"]}
            lesson_ok = lesson_ok and e["status"] == "done"
        prior_done = prior_done and info["status"] == "done"
    return nxt or {}


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def write_state(model: dict, labs: dict, solution: bool) -> dict:
    nxt = add_unlocks(model, labs)
    state = {
        "generatedAt": time.time(),
        "solution": solution,
        "labs": labs,
        "total": {"passed": sum(l["passed"] for l in labs.values()), "total": sum(l["total"] for l in labs.values())},
        "next": nxt,
    }
    STATE.parent.mkdir(exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(STATE)  # atomic, so watchers never read a half-written file
    return state


def update(labs_to_run: list[int] | None = None, solution: bool = False) -> dict:
    model = labmodel.build_model()
    by_n = {l["n"]: l for l in model["labs"]}
    run = labs_to_run or list(by_n)
    labs = {} if not labs_to_run else dict(load_state().get("labs", {}))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, (tests, output, error) in zip(run, pool.map(lambda n: run_lab(n, solution), run)):
            labs[str(n)] = summarize(by_n[n], tests, output, error)
    return write_state(model, labs, solution)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lab", type=int, action="append", help="run only this lab (repeatable)")
    p.add_argument("--solution", action="store_true", help="grade the reference solution")
    p.add_argument("--print", action="store_true", help="print a short scoreboard")
    a = p.parse_args()
    state = update(a.lab, a.solution)
    if a.print:
        t = state["total"]
        for n, info in state["labs"].items():
            print(f"Lab {n}: {info['passed']}/{info['total']} {info['status']}"
                  + (f"  (could not run: {info['error']})" if info.get("error") else ""))
        print(f"Total: {t['passed']}/{t['total']}")


if __name__ == "__main__":
    main()
