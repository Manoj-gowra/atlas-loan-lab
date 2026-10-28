"""LAB 3 - Exercise 3.4: Atlas's external data sources as an MCP server, scoped per client.

Lesson 3.4: the investigator's sources (credit bureau, public records, industry data) are an
EVOLVING set reused by several clients - the specialists, Claude Code on a developer's laptop, an
analyst's desktop - which is exactly what MCP's discovery layer is for. But an MCP server that
exposes its full catalog to every client just moves capability bloat (3.1) onto a new mechanism:
expose to each client only what its task needs.

Run it (all read-only tools) for Claude Code with:  python -m atlas.mcp_server
Requires: pip install "mcp>=2.2,<3"
"""
from __future__ import annotations

import sys
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import data_access

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def get_business_credit_report(customer_id: str) -> dict[str, Any]:
    """Read-only. Business credit bureau report: score (0-300), days beyond terms, liens, judgments."""
    return data_access.get_business_credit_report(customer_id)


def get_public_filings(customer_id: str, years: int = 3) -> dict[str, Any]:
    """Read-only. UCC liens, tax liens and judgments filed in the last N years."""
    return data_access.get_public_filings(customer_id, years)


def get_industry_risk(customer_id: str) -> dict[str, Any]:
    """Read-only. Sector, NAICS code, sector stress index (0-100) and outlook."""
    return data_access.get_industry_risk(customer_id)


def get_verified_financials(customer_id: str) -> dict[str, Any]:
    """Read-only. Tax-return verified revenue and EBITDA."""
    return data_access.get_verified_financials(customer_id)


SOURCES: dict[str, Callable[..., Any]] = {f.__name__: f for f in (
    get_business_credit_report, get_public_filings, get_industry_risk, get_verified_financials)}

CLIENT_EXPOSURE: dict[str, set[str]] = {
    "investigator": set(),       # TODO
    "analyst_desktop": set(),    # TODO
    "claude_code": set(),        # TODO
}


def build_server(client: str = "investigator") -> MCPServer:
    """An MCP server exposing ONLY CLIENT_EXPOSURE[client] (unknown client -> KeyError), each tool
    registered with annotations=READ_ONLY. Docstrings become descriptions; type hints the schema."""
    server = MCPServer(name="atlas-bureau", instructions="Read-only Atlas Financial bureau and industry data by "
                                                         "business customer ID (B-1234).")
    # TODO (Lab 3): For each exposed name (sorted), register SOURCES[name] with
    #   server.tool(annotations=READ_ONLY)(fn).
    raise NotImplementedError("Lab 3: implement build_server()")
    return server


if __name__ == "__main__":
    build_server(sys.argv[1] if len(sys.argv) > 1 else "claude_code").run("stdio")
