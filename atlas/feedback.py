"""The feedback loop: the fourth stage of every architecture.

  1.4 (Lab 1)  record()                  - capture the ORIGINAL output, the CORRECTED value and the context
  3.6 (Lab 3)  correction_rate_by_field()- a live signal to alert on (observability)
  4.2 (Lab 4)  to_golden_rows()          - corrections become new evaluation cases

"We log everything" is not a feedback loop. A feedback loop records the PAIR - what the system
produced and what a person changed it to - plus which field, step and component, so the gap can be
measured later.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config


class FeedbackStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config.RUNS / "feedback.jsonl")

    def all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def record(
        self,
        app_id: str,
        component: str,
        step: str,
        field: str,
        original: Any,
        corrected: Any,
        officer_id: str,
    ) -> dict:
        """Lesson 1.4. Append one JSON line {"app_id", "component", "step", "field", "original",
        "corrected", "officer_id", "ts"} and return it. Refuse (ValueError) a record missing either
        side of the pair - original or corrected is None - because half a pair measures nothing.
        """
        # TODO (Lab 1): Validate both sides of the pair, build the dict, append it as a JSON line.
        if original is None or corrected is None:
            raise ValueError(
                "A feedback record needs BOTH the original output and the corrected value"
            )
        item = {
            "app_id": app_id,
            "component": component,
            "step": step,
            "field": field,
            "original": original,
            "corrected": corrected,
            "officer_id": officer_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(item, default=str) + "\n")
        return item
        # raise NotImplementedError("Lab 1: implement record()")

    def correction_rate_by_field(self, cases_reviewed: int) -> dict[str, float]:
        """Lesson 3.6. For each field: corrections / cases_reviewed (empty dict if nothing reviewed).
        A rising rate on ONE field is the earliest sign of a changed format or a stale index.
        """
        # TODO (Lab 3): Count corrections per field with a Counter and divide by cases_reviewed.
        raise NotImplementedError("Lab 3: implement correction_rate_by_field()")

    def to_golden_rows(self) -> list[dict]:
        """Lesson 4.2. One regression case per app_id: {"app_id", "category": "officer_correction",
        "expected_fields": {field: corrected, ...}}. Later corrections of a field win.
        """
        # TODO (Lab 4): Group records by app_id into expected_fields dicts.
        raise NotImplementedError("Lab 4: implement to_golden_rows()")
