"""Test setup. Run your code:  pytest tests/test_lab1.py
Run the reference solution:   pytest tests/test_lab1.py --solution
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser):
    parser.addoption("--solution", action="store_true", default=False,
                     help="run the tests against solutions/ instead of your code")


def pytest_configure(config):
    base = ROOT / "solutions" if config.getoption("--solution") else ROOT
    sys.path.insert(0, str(base))
    os.environ["ATLAS_MODE"] = "fake"  # tests are only deterministic with the offline model
    os.environ.pop("ATLAS_POLICY_DIR", None)


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    """Every test gets an empty runs/ folder, a fresh fake model, the real policy folder,
    a working authorization service and reset simulations."""
    from atlas import authz, config, data_access, llm

    monkeypatch.setattr(config, "RUNS", tmp_path / "runs")
    monkeypatch.delenv("ATLAS_POLICY_DIR", raising=False)
    monkeypatch.setattr(authz.AUTHZ, "outage", False)
    llm.reset_client()
    data_access.reset_simulations()
    yield
