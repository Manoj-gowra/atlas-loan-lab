"""LAB 7 - Exercise 7.2: give the debugging assistant SCOPED, READ-ONLY access to real signals.

Course lesson 7.2: reasoning from code alone answers "what COULD cause this"; logs and traces answer
"what DID happen" and "is the proposed cause right". So connect Claude Code to the traces and the
change log - read-only, and only those (least privilege for operational data, 7.1).

Registered in .mcp.json as "atlas-ops". Run by hand: python -m atlas.ops_mcp
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import config

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def _safe_trace_path(trace_id: str) -> Path:
    """Given: refuse anything that is not a plain trace id (no paths, no traversal)."""
    if not trace_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("trace_id must be a plain id like APP-006")
    return config.RUNS / "traces" / f"{trace_id}.jsonl"


def list_traces() -> list[str]:
    """Read-only. Trace ids available under runs/traces."""
    folder = config.RUNS / "traces"
    return sorted(p.stem for p in folder.glob("*.jsonl")) if folder.exists() else []


def get_trace(trace_id: str) -> list[dict[str, Any]]:
    """Read-only. The spans of one trace (model calls, tool calls, retrievals) with their attributes."""
    path = _safe_trace_path(trace_id)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def get_change_log() -> list[dict[str, Any]]:
    """Read-only. Deployments, policy publications and index builds, oldest first."""
    entries = []
    log = config.RUNS / "change_log.jsonl"
    if log.exists():
        entries += [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    build_log = config.RUNS / "index_build.log"
    if build_log.exists():
        for line in build_log.read_text().splitlines():
            ts, _, rest = line.partition(" ")
            entries.append({"ts": ts, "what": f"index: {rest}"})
    return sorted(entries, key=lambda e: e["ts"])


def build_server() -> MCPServer:
    """Register list_traces, get_trace and get_change_log - and nothing else - each with READ_ONLY."""
    server = MCPServer(name="atlas-ops", instructions="Read-only access to Atlas traces and the change log.")
    for fn in (list_traces, get_trace, get_change_log):
        server.tool(annotations=READ_ONLY)(fn)
    return server


if __name__ == "__main__":
    build_server().run("stdio")
