"""LAB 7 - Developer productivity and enablement (course Chapter 7).

    pytest tests/test_lab7.py [--solution]
Guide: docs/LAB7.md. You configure Claude Code for the TEAM: CLAUDE.md, .claude/settings.json,
.claude/skills/, and you give the debugging assistant scoped, read-only access to real signals.
"""
import asyncio
import importlib.util
import json
import re
import subprocess
import sys

import pytest
from _helpers import process

from atlas import config
from atlas.devtools import summarize_failures, verify_hypothesis
from atlas.tracing import load_trace

BASE = config.WORKSPACE            # your project root, or solutions/ with --solution
ROOT = config.ROOT                 # where scripts/ and .mcp.json live


def no_todo(path):
    assert path.exists(), f"missing {path}"
    text = path.read_text()
    assert "TODO" not in text, f"{path.relative_to(ROOT)} still has TODOs"
    return text


# ====================================================================== 7.1 Configuring Claude tooling for teams


def test_7_1_claude_md_is_the_shared_baseline():
    text = no_todo(BASE / "CLAUDE.md")
    assert len(text.splitlines()) <= 60, "keep project memory short enough that it is read"
    lowered = text.lower()
    assert "pytest" in lowered and "check.py" in lowered, "how tests are run"
    assert any("runs/" in ln and "generated" in ln.lower() for ln in text.splitlines()), \
        "say which directory is GENERATED output, not source"
    for item in ("fake_claude.py", "tests/", "solutions/", "llm.call", "execute_tool", "ssn", "rebuild_index"):
        assert item in lowered or item in text, f"CLAUDE.md should mention {item}"


def _settings():
    return json.loads((BASE / ".claude" / "settings.json").read_text())


def test_7_1_permission_policy_least_privilege_for_the_assistant():
    perms = _settings()["permissions"]
    allow, ask, deny = perms.get("allow", []), perms.get("ask", []), perms.get("deny", [])
    assert any(r.startswith("Bash(pytest") or "pytest" in r for r in allow), "running tests should not need a prompt"
    assert "Bash(git push *)" in ask, "pushing needs explicit confirmation every time"
    assert any("data/policies" in r for r in ask) and any("atlas/rules.py" in r for r in ask), \
        "compliance-relevant files (policies, the rules engine) need confirmation every time"
    assert any(r.startswith("Read(") and ".env" in r for r in deny), "secrets are never read"
    assert any(r.startswith("Read(") and "data/.fake" in r for r in deny), "the answer key is off limits"
    broad = [r for r in allow if r in ("Bash", "Bash(*)", "Edit", "Edit(*)", "Edit(./**)", "Write")]
    assert not broad, f"broad access 'for convenience' is the anti-pattern: {broad}"
    assert not set(allow) & set(ask), "a rule can't be both allowed and confirmed"


def _hook_command(event: str, needle: str) -> str:
    entries = _settings().get("hooks", {}).get(event, [])
    for entry in entries:
        if "Edit" in entry.get("matcher", "") and "Write" in entry.get("matcher", ""):
            for hook in entry.get("hooks", []):
                if needle in hook.get("command", ""):
                    return hook["command"]
    raise AssertionError(f"no {event} hook for Edit|Write running {needle}")


def _run_hook(script: str, file_path: str) -> int:
    event = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "hooks" / script)], input=event,
                          capture_output=True, text=True).returncode


def test_7_1_hooks_turn_guidance_into_enforcement():
    _hook_command("PreToolUse", "protect_files.py")
    _hook_command("PostToolUse", "check_syntax.py")
    assert _run_hook("protect_files.py", str(ROOT / "runs" / "traces" / "APP-001.jsonl")) == 2, "generated output"
    assert _run_hook("protect_files.py", str(ROOT / "tests" / "test_lab1.py")) == 2
    assert _run_hook("protect_files.py", str(ROOT / "atlas" / "fake_claude.py")) == 2
    assert _run_hook("protect_files.py", str(ROOT / "atlas" / "rules.py")) == 0


def _skill(name: str) -> tuple[dict, str]:
    text = no_todo(BASE / ".claude" / "skills" / name / "SKILL.md")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert match, f"{name}: SKILL.md needs YAML frontmatter between --- lines"
    meta = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in meta.items()}, match.group(2)


def test_7_1_reusable_workflow_test_summary():
    meta, body = _skill("test-summary")
    assert meta["name"] == "test-summary"
    assert len(meta["description"].split()) >= 10 and "use" in meta["description"].lower(), \
        "the description says WHAT it does and WHEN to use it - Claude picks skills by it"
    assert "scripts/test_summary.py" in body


def test_7_1_reusable_workflow_policy_change():
    meta, body = _skill("policy-change")
    assert meta["name"] == "policy-change" and len(meta["description"].split()) >= 10
    for must in ("data/policies", "RULEBOOK", "effective_from", "rebuild_index.py", "RUNBOOK"):
        assert must in body, f"the policy-change procedure must cover {must}"
    assert body.index("RULEBOOK") < body.index("rebuild_index.py"), "rebuild the index after changing the rules"


def test_7_1_summarize_failures_by_lab():
    out = """
FAILED tests/test_lab3.py::test_3_2_the_gate_fails_secure - AssertionError: boom
ERROR tests/test_lab1.py::test_1_1_value_numbers_from_discovery - NotImplementedError
FAILED tests/test_lab3.py::test_3_3_one_chunk_per_numbered_rule - assert 1 == 2
3 failed, 40 passed in 1.2s
"""
    assert summarize_failures(out) == {"lab1": ["test_1_1_value_numbers_from_discovery"],
                                       "lab3": ["test_3_2_the_gate_fails_secure", "test_3_3_one_chunk_per_numbered_rule"]}
    assert summarize_failures("all good") == {}


# ====================================================================== 7.2 AI-assisted debugging


def test_7_2_verify_the_hypothesis_against_the_trace():
    process("APP-006")
    spans = load_trace(config.RUNS / "traces" / "APP-006.jsonl")
    right = {"claim": "the bank statement service timed out once and was retried",
             "evidence": [{"span": "tool:get_bank_statements", "attr": "is_error", "equals": True},
                          {"span": "tool:get_bank_statements", "attr": "is_error", "equals": False}]}
    result = verify_hypothesis(right, spans)
    assert result["verified"] and len(result["supported"]) == 2
    confident_but_wrong = {"claim": "the industry data call failed, so the sector risk is missing",
                           "evidence": [{"span": "tool:get_industry_risk", "attr": "is_error", "equals": True},
                                        {"span": "tool:get_bank_statements", "attr": "is_error", "equals": True}]}
    result = verify_hypothesis(confident_but_wrong, spans)
    assert not result["verified"] and len(result["unsupported"]) == 1
    assert verify_hypothesis({"claim": "from reading the code", "evidence": []}, spans)["verified"] is False


needs_mcp = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="pip install 'mcp>=2.2,<3'")


@needs_mcp
def test_7_2_ops_server_is_scoped_and_read_only():
    from atlas.mcp_bridge import call_tool, list_tools_async
    from atlas.ops_mcp import build_server
    tools = asyncio.run(list_tools_async(build_server()))
    assert {t["name"] for t in tools} == {"list_traces", "get_trace", "get_change_log"}
    assert all(t["read_only"] for t in tools)
    process("APP-001")
    listing = call_tool(build_server(), "list_traces", {})
    assert "APP-001" in listing.content
    mcp = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
    assert mcp["atlas-bureau"]["args"][-1] == "claude_code", "Claude Code gets its own scoped exposure"
    assert mcp["atlas-ops"]["args"][-1] == "atlas.ops_mcp"


@needs_mcp
def test_7_2_correlate_timing_with_the_change_log():
    from atlas.diagnosis import what_changed
    from atlas.mcp_bridge import list_tools_async
    from atlas.ops_mcp import build_server
    assert "get_change_log" in {t["name"] for t in asyncio.run(list_tools_async(build_server()))}
    from atlas.ops_mcp import get_change_log
    config.RUNS.mkdir(parents=True, exist_ok=True)
    (config.RUNS / "change_log.jsonl").write_text(
        '{"ts": "2026-10-20T10:00:00+00:00", "what": "deploy: intake_v2 prompt"}\n'
        '{"ts": "2026-10-28T16:00:00+00:00", "what": "policy: POL-TERM v4 published"}\n')
    (config.RUNS / "index_build.log").write_text(
        "2026-10-27T02:00:00+00:00 built index from data/policies (nightly)\n")
    log = get_change_log()
    assert [e["ts"][:10] for e in log] == ["2026-10-20", "2026-10-27", "2026-10-28"]
    culprit = what_changed(log, "2026-10-30T09:00:00+00:00")
    assert culprit["what"] == "policy: POL-TERM v4 published", "a policy change with no index build after it"
