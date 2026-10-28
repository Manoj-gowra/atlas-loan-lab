"""Claude Code PreToolUse hook: block edits to files that define the lab or are generated.

Claude Code sends the tool call as JSON on stdin. Exit code 2 BLOCKS the call and shows stderr to
Claude. Guidance vs enforcement again (2.3, 7.1): CLAUDE.md asks; this hook makes it impossible.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # the project folder (scripts/hooks/ is two levels down)
PROTECTED = ("atlas/fake_claude.py", "data/.fake/", "tests/", "solutions/", "runs/")

event = json.load(sys.stdin)
raw = (event.get("tool_input") or {}).get("file_path", "")
path = Path(raw)
try:
    rel = path.resolve().relative_to(ROOT).as_posix() if path.is_absolute() else path.as_posix()
except ValueError:
    sys.exit(0)  # outside the project: not ours to police
if any(rel == p or rel.startswith(p) for p in PROTECTED):
    print(f"Blocked: {rel} is part of the lab definition or generated output and must not be edited. "
          "Change your own code in atlas/, prompts/ or docs/ instead.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
