from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from importlib.machinery import SourceFileLoader


ROOT = Path(__file__).resolve().parents[1]
FETCHER = ROOT / "bundle" / "bin" / "agentfeeds-fetch"


def load_fetcher():
    loader = SourceFileLoader("agentfeeds_fetch", str(FETCHER))
    spec = importlib.util.spec_from_loader("agentfeeds_fetch", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_state_path_for_stream_matches_spec_examples(tmp_path):
    fetcher = load_fetcher()

    assert fetcher.state_path_for_stream(
        "feed://weather.gov/forecast?lat=37.33&lon=-121.89",
        tmp_path,
    ) == tmp_path / "state" / "weather.gov" / "forecast.lat=37.33,lon=-121.89.json"

    assert fetcher.state_path_for_stream(
        "feed://github.com/repos/anthropics/claude-code/releases",
        tmp_path,
    ) == tmp_path / "state" / "github.com" / "repos.anthropics.claude-code.releases.json"


def test_atomic_write_json_writes_complete_file(tmp_path):
    fetcher = load_fetcher()
    target = tmp_path / "state" / "example.com" / "stream.json"

    fetcher.atomic_write_json(target, {"ok": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert not target.with_suffix(".json.tmp").exists()
