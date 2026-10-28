"""LAB 5 - Exercises 5.2/5.3 (and the 2.3 example): the approval gate and the audit trail.

The ONLY code path that may set an application's official status. It enforces, in code:
  - a person decides (General Standards 3.1; GDPR limits on automated decisions - 5.3)
  - DOLLAR-LIMITED authority: a loan officer signs up to $500,000, a senior credit officer up to
    $2,000,000, larger loans need the credit committee (lesson 2.3's "$500,000 second reviewer"
    rule, as enforcement instead of a prompt sentence)
  - an override of the system's recommendation needs a reason (3.3)
Every decision goes into a tamper-evident, hash-chained audit log: who did what, when (5.3).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, data_access

AUTHORITY_LIMITS = {"loan_officer": 500_000, "senior_credit_officer": 2_000_000, "credit_committee": float("inf")}


@dataclass(frozen=True)
class Approver:
    approver_id: str
    role: str


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config.RUNS / "audit.jsonl")

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    @staticmethod
    def _hash(prev_hash: str, body: dict) -> str:
        return hashlib.sha256((prev_hash + json.dumps(body, sort_keys=True, default=str)).encode()).hexdigest()

    def append(self, event: dict) -> dict:
        """Write {"event", "ts", "prev_hash" (last entry's hash or "GENESIS"),
        "hash": _hash(prev_hash, {"event": event, "ts": ts})} as one JSON line; return it."""
        # TODO (Lab 5): Read the last hash, compute this one, append.
        raise NotImplementedError("Lab 5: implement append()")

    def verify(self) -> bool:
        """True when every entry's prev_hash and hash are consistent from the start."""
        # TODO (Lab 5): Walk the chain recomputing hashes.
        raise NotImplementedError("Lab 5: implement verify()")


class ApprovalGate:
    def __init__(self, audit: AuditLog | None = None) -> None:
        self.audit = audit or AuditLog()

    def finalize(self, case: Any, approver: Approver | None, decision: str, reason: str = "") -> dict:
        """Record an authorized person's decision.
          no approver                                         -> PermissionError
          decision not "approve"/"decline"                    -> ValueError
          amount > AUTHORITY_LIMITS[approver.role]            -> PermissionError naming the authority needed
          case.recommendation set and decision differs, no reason -> ValueError (overrides need a reason)
        then data_access.update_application_status(case.app_id, "approved"/"declined", reason) and return
        self.audit.append({"type": "decision", "app_id", "approver_id", "role", "decision",
                           "recommendation", "override", "amount", "reason"})."""
        # TODO (Lab 5): Four checks in order, then the write and the audit entry.
        raise NotImplementedError("Lab 5: implement finalize()")
