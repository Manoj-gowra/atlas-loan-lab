"""The bank's "systems": application documents, bureau and verification services, and two
write operations. GIVEN FILE.

In Lab 3 you decide which of these each component may reach (3.1 capability bloat) and enforce it
at the tool-call gate (3.2). Notice the write operations live here too - least privilege is about
what you EXPOSE, to whom.
"""
from __future__ import annotations

import json
from functools import lru_cache

from . import config


class ServiceUnavailable(Exception):
    """A downstream system timed out (simulated)."""


def _app_paths(app_id: str) -> list:
    return [config.DATA / "applications" / f"{app_id}.txt", config.DATA / "drills" / "applications" / f"{app_id}.txt"]


def load_application_text(app_id: str) -> str:
    for path in _app_paths(app_id):
        if path.exists():
            return path.read_text()
    raise FileNotFoundError(f"No application document {app_id}")


def list_application_ids(include_drills: bool = False) -> list[str]:
    ids = sorted(p.stem for p in (config.DATA / "applications").glob("APP-*.txt"))
    if include_drills:
        ids += sorted(p.stem for p in (config.DATA / "drills" / "applications").glob("APP-*.txt"))
    return ids


@lru_cache(maxsize=None)
def _bureau(name: str) -> dict:
    return json.loads((config.DATA / "bureau" / f"{name}.json").read_text())


def _need(table: str, customer_id: str) -> dict:
    record = _bureau(table).get(customer_id)
    if record is None:
        raise KeyError(f"No {table.replace('_', ' ')} record for customer {customer_id}")
    return record


def get_business_credit_report(customer_id: str) -> dict:
    return {"customer_id": customer_id, **_need("credit_reports", customer_id)}


_flaky_calls: dict[str, int] = {}


def get_bank_statements(customer_id: str, months: int = 6) -> dict:
    """Last N months (max 12), newest last. The service times out on the first call for B-1006."""
    if customer_id == "B-1006":
        _flaky_calls[customer_id] = _flaky_calls.get(customer_id, 0) + 1
        if _flaky_calls[customer_id] == 1:
            raise ServiceUnavailable("bank statement service timed out after 10s")
    rows = _need("bank_statements", customer_id)
    months = max(1, int(months))
    out = {"customer_id": customer_id, "statements": rows[-min(months, 12):]}
    if months > 12:
        out["note"] = "Only 12 months of history are available."
    return out


def get_verified_financials(customer_id: str) -> dict:
    return {"customer_id": customer_id, **_need("verified_financials", customer_id)}


def get_public_filings(customer_id: str, years: int = 3) -> dict:
    _need("business_profiles", customer_id)
    rows = _bureau("public_filings").get(customer_id, [])
    cutoff = 2026 - max(1, int(years))
    return {"customer_id": customer_id, "years": years,
            "filings": [r for r in rows if int(r["date"][:4]) > cutoff]}


def get_business_profile(customer_id: str) -> dict:
    return {"customer_id": customer_id, **_need("business_profiles", customer_id)}


def get_industry_risk(customer_id: str) -> dict:
    profile = get_business_profile(customer_id)
    return {"customer_id": customer_id, "naics": profile["naics"], "sector": profile["sector"],
            **_bureau("industry_risk")[profile["naics"]]}


# ---------------------------------------------------------------- write operations

def _status_path():
    return config.RUNS / "status.json"


def update_application_status(application_id: str, status: str, note: str = "") -> dict:
    """WRITE: changes an application's official status. Only the approval gate may call this."""
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {}
    data[application_id] = {"status": status, "note": note}
    path.write_text(json.dumps(data, indent=2))
    return {"application_id": application_id, "status": status}


def disburse_funds(application_id: str, amount: float) -> dict:
    """WRITE: moves money. Nothing in the AI system should ever be able to reach this."""
    path = config.RUNS / "disbursements.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else []
    data.append({"application_id": application_id, "amount": amount})
    path.write_text(json.dumps(data, indent=2))
    return {"application_id": application_id, "disbursed": amount}


def read_statuses() -> dict:
    path = _status_path()
    return json.loads(path.read_text()) if path.exists() else {}


def read_disbursements() -> list:
    path = config.RUNS / "disbursements.json"
    return json.loads(path.read_text()) if path.exists() else []


def reset_simulations() -> None:
    _flaky_calls.clear()
