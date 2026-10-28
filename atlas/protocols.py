"""LAB 3 - Exercise 3.4: integration protocols - MCP, direct API/CLI, agent-to-agent - and
progressive discovery of tools.

Course lesson 3.4:
  MCP              - a capability REUSED across agents/clients, or a set that GROWS or CHANGES
  direct API/CLI   - one stable, well-understood connection nobody else will discover or reuse
  agent-to-agent   - a genuinely AUTONOMOUS peer outside your control (a partner bank's AI on a
                     syndicated loan): send a goal, treat it as crossing a real boundary
Progressive discovery: with many connected tools, load only the definitions the current task needs
(it saves context AND avoids the >5-tool selection problem from 1.3).
Protocol choice never replaces least privilege: an MCP server still exposes per client only what
that client's task needs (see mcp_server.py).
"""
from __future__ import annotations


def choose_protocol(*, autonomous_external_peer: bool = False, reused_or_evolving: bool = False,
                    single_stable_connection: bool = False) -> str:
    """Return "agent_to_agent", "mcp" or "direct_api" (check in that order). ValueError if no signal."""
    # TODO (Lab 3): Three ifs in the docstring's order.
    raise NotImplementedError("Lab 3: implement choose_protocol()")


def select_tools(task_keywords: set[str], catalog: dict[str, str], limit: int = 5) -> list[str]:
    """Progressive discovery. catalog maps tool name -> description. Score each tool by how many
    task_keywords (lower-case) appear in its name or description (lower-case); keep tools with a
    score above 0, highest score first (ties by name), at most `limit`."""
    # TODO (Lab 3): Score, filter > 0, sort by (-score, name), slice.
    raise NotImplementedError("Lab 3: implement select_tools()")
