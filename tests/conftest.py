from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def use_fixture_catalog(monkeypatch):
    monkeypatch.setenv("AGENTFEEDS_CATALOG_DIR", str(ROOT / "tests" / "fixtures" / "catalog"))
