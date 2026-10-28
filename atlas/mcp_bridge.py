"""Given: connect an MCP server to the Claude Messages API.

An MCP client discovers tools at runtime (list_tools) and calls them (call_tool). This bridge
converts MCP tool listings into Claude `tools` definitions, and MCP results into tool_result
content - which is all that "using MCP with the API" means under the hood.

The in-memory Client(server) is for tests; for a separate process use the stdio transport.
"""
from __future__ import annotations

import asyncio
from typing import Any

from mcp.client.client import Client

from .gate import ToolOutcome


async def list_tools_async(server: Any) -> list[dict]:
    async with Client(server) as client:
        listing = await client.list_tools()
    return [{
        "name": t.name,
        "description": t.description or "",
        "input_schema": t.input_schema,
        "read_only": bool(t.annotations and t.annotations.read_only_hint),
    } for t in listing.tools]


async def call_tool_async(server: Any, name: str, args: dict) -> ToolOutcome:
    async with Client(server) as client:
        result = await client.call_tool(name, args)
    text = "\n".join(getattr(c, "text", "") for c in result.content)
    return ToolOutcome(content=text, is_error=bool(result.is_error), authorized=True, executed=not result.is_error)


def claude_tool_defs(server: Any) -> list[dict]:
    """MCP listing -> Claude API tool definitions (name, description, input_schema)."""
    return [{k: t[k] for k in ("name", "description", "input_schema")} for t in asyncio.run(list_tools_async(server))]


def call_tool(server: Any, name: str, args: dict) -> ToolOutcome:
    return asyncio.run(call_tool_async(server, name, args))
