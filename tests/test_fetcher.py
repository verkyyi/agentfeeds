from __future__ import annotations

import json
from pathlib import Path
import textwrap

import agentfeeds.fetch as fetcher

ROOT = Path(__file__).resolve().parents[1]


def test_state_path_for_stream_matches_spec_examples(tmp_path):
    assert fetcher.state_path_for_stream(
        "feed://weather.gov/forecast?lat=37.33&lon=-121.89",
        tmp_path,
    ) == tmp_path / "state" / "weather.gov" / "forecast.lat=37.33,lon=-121.89.json"

    assert fetcher.state_path_for_stream(
        "feed://github.com/repos/anthropics/claude-code/releases",
        tmp_path,
    ) == tmp_path / "state" / "github.com" / "repos.anthropics.claude-code.releases.json"


def test_atomic_write_json_writes_complete_file(tmp_path):
    target = tmp_path / "state" / "example.com" / "stream.json"

    fetcher.atomic_write_json(target, {"ok": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert not target.with_suffix(".json.tmp").exists()


def test_once_fetch_writes_snapshot_state_and_catalog(tmp_path, monkeypatch):
    (tmp_path / "subscriptions.yaml").write_text(
        textwrap.dedent(
            """
            version: "0.3"
            defaults:
              poll_interval_seconds: 600
              history_limit: 50
            subscriptions:
              - id: weather/santa-clara-current
                title: Santa Clara current weather
                provider: weather/openmeteo-current
                parameters:
                  lat: 37.33
                  lon: -121.89
            """
        ),
        encoding="utf-8",
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "latitude": 37.33,
                "longitude": -121.89,
                "current": {
                    "time": "2026-05-01T12:00",
                    "temperature_2m": 22.1,
                    "relative_humidity_2m": 47,
                    "wind_speed_10m": 9.4,
                    "weather_code": 1,
                },
            }

    monkeypatch.setattr(fetcher.requests, "request", lambda *args, **kwargs: FakeResponse())

    assert fetcher.main(["--root", str(tmp_path), "--once", "weather/santa-clara-current"]) == 0

    state_path = tmp_path / "state" / "api.open-meteo.com" / "v1.forecast.latitude=37.33,longitude=-121.89.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["_meta"]["subscription_id"] == "weather/santa-clara-current"
    assert state["_meta"]["provider_id"] == "weather/openmeteo-current"
    assert state["_meta"]["title"] == "Santa Clara current weather"
    assert state["_meta"]["stale"] is False
    assert state["data"]["temperature_c"] == 22.1
    catalog = (tmp_path / "catalog.md").read_text(encoding="utf-8")
    assert "weather/santa-clara-current" in catalog
    assert "weather/openmeteo-current" in catalog


def test_event_state_merges_dedups_and_truncates(tmp_path):
    stream = {
        "id": "dev/example",
        "title": "Example events",
        "type": "example.event",
        "mode": "event",
        "schema_url": "https://agentfeeds.dev/schemas/example.event.v1.json",
        "schema_version": "1.0.0",
    }
    stream_uri = "feed://example.com/events"
    existing = {
        "_meta": {},
        "data": [
            {"id": "b", "data": {"value": 2}},
            {"id": "a", "data": {"value": 1}},
        ],
    }
    events = [
        {"id": "c", "data": {"value": 3}},
        {"id": "b", "data": {"value": 22}},
    ]

    subscription = {"id": "dev/example-instance", "title": "Example instance", "provider": "dev/example"}
    payload = fetcher.state_payload(subscription, stream, stream_uri, events, existing, 600, 2)

    assert [event["id"] for event in payload["data"]] == ["c", "b"]
    assert payload["data"][1]["data"]["value"] == 22


def test_local_file_fetch_writes_snapshot_state(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nLocal context.\n", encoding="utf-8")
    agentfeeds_root = tmp_path / "agentfeeds"
    (agentfeeds_root / "subscriptions.yaml").parent.mkdir(parents=True)
    (agentfeeds_root / "subscriptions.yaml").write_text(
        textwrap.dedent(
            f"""
            version: "0.3"
            defaults:
              poll_interval_seconds: 600
              history_limit: 50
            subscriptions:
              - id: local/notes-md
                title: notes.md
                provider: local/file
                parameters:
                  path: {source}
            """
        ),
        encoding="utf-8",
    )

    assert fetcher.main(["--root", str(agentfeeds_root), "--once", "local/notes-md"]) == 0

    state_files = list((agentfeeds_root / "state" / "local.file").glob("**/*.json"))
    assert len(state_files) == 1
    assert state_files[0].name.startswith("file.notes.md.")
    state = json.loads(state_files[0].read_text(encoding="utf-8"))
    assert state["_meta"]["subscription_id"] == "local/notes-md"
    assert state["_meta"]["provider_id"] == "local/file"
    assert state["data"]["path"] == str(source)
    assert state["data"]["name"] == "notes.md"
    assert state["data"]["content"] == "# Notes\n\nLocal context.\n"
    assert len(state["data"]["sha256"]) == 64
