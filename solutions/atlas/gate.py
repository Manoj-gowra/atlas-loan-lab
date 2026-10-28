"""LAB 3 - Exercise 3.2 (+ 5.1): the tool-call gate - the ONE place a tool call can execute.

Every tool call any agent makes goes through execute_tool(). It:
  1. asks the authorization service (3.2) - and FAILS SECURE if that service is down (5.1):
     an outage in the authorization path is not evidence the action is safe;
  2. dispatches to the implementation;
  3. turns every failure into a tool_result the model can read (errors are results, not crashes).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import data_access
from .authz import AUTHZ, AuthorizationService, AuthorizationUnavailable, CaseContext
from .tools import IMPLEMENTATIONS, TERMINAL_TOOL, to_json


@dataclass
class ToolOutcome:
    content: str
    is_error: bool
    authorized: bool
    executed: bool


def execute_tool(component: str, tool: str, args: dict, ctx: CaseContext,
                 authz: AuthorizationService = AUTHZ) -> ToolOutcome:
    """Run one tool call safely. NEVER raise.

      authz.check(...) raises AuthorizationUnavailable -> ToolOutcome("Authorization service unavailable:
                         call denied (fail secure). Do not retry; report it as unable to check.", True, False, False)
      decision not allowed                -> ToolOutcome(f"Not authorized: {reason}", True, False, False)
      tool == TERMINAL_TOOL               -> error, not executable (authorized True, executed False)
      no implementation                   -> error "Unknown tool" (authorized True, executed False)
      success                             -> ToolOutcome(to_json(result), False, True, True)
      data_access.ServiceUnavailable      -> "Temporary error: ... You may retry this call once." (True, True, True)
      KeyError / ValueError / TypeError   -> f"Error: {exc}" (True, True, True)
    """
    try:
        decision = authz.check(component, tool, args, ctx)
    except AuthorizationUnavailable:
        return ToolOutcome("Authorization service unavailable: call denied (fail secure). Do not retry; report it "
                           "as unable to check.", True, False, False)
    if not decision.allowed:
        return ToolOutcome(f"Not authorized: {decision.reason}", True, False, False)
    if tool == TERMINAL_TOOL:
        return ToolOutcome(f"{TERMINAL_TOOL} ends the investigation and is not executed as a tool.", True, True, False)
    fn = IMPLEMENTATIONS.get(tool)
    if fn is None:
        return ToolOutcome(f"Unknown tool '{tool}'.", True, True, False)
    try:
        return ToolOutcome(to_json(fn(args, ctx)), False, True, True)
    except data_access.ServiceUnavailable as exc:
        return ToolOutcome(f"Temporary error: {exc}. You may retry this call once.", True, True, True)
    except (KeyError, ValueError, TypeError) as exc:
        return ToolOutcome(f"Error: {exc}", True, True, True)
