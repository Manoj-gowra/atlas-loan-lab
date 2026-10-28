"""Claude Code PostToolUse hook: after Claude edits a Python file, make sure it still compiles.

On a syntax error, exit code 2 sends the error back to Claude so it fixes it immediately,
instead of you finding out later from a failing test run.
"""
import json
import py_compile
import sys

event = json.load(sys.stdin)
path = (event.get("tool_input") or {}).get("file_path", "")
if path.endswith(".py"):
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        print(f"Syntax error after editing {path}:\n{exc.msg}", file=sys.stderr)
        sys.exit(2)
sys.exit(0)
