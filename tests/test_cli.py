from __future__ import annotations

import json
from pathlib import Path

import yaml

from agentfeeds import cli


def test_cli_subscribe_status_and_unsubscribe_without_fetch(tmp_path, capsys):
    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "weather/openmeteo-current",
        "lat=37.3541",
        "lon=-121.9552",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == [
        {
            "id": "weather/openmeteo-current",
            "parameters": {"lat": 37.3541, "lon": -121.9552},
        }
    ]

    assert cli.main(["--root", str(tmp_path), "status", "--json"]) == 0
    status_out = capsys.readouterr().out
    status = json.loads(status_out[status_out.index("{"):])
    assert status["subscriptions"][0]["id"] == "weather/openmeteo-current"
    assert status["subscriptions"][0]["exists"] is False

    assert cli.main([
        "--root",
        str(tmp_path),
        "unsubscribe",
        "weather/openmeteo-current",
    ]) == 0
    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == []


def test_cli_discover_filters_catalog(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "discover", "hacker"]) == 0
    out = capsys.readouterr().out
    assert "dev/hackernews-frontpage" in out
    assert "weather/openmeteo-current" not in out


def test_cli_refuses_ambiguous_unsubscribe(tmp_path):
    config = {
        "version": "0.3",
        "defaults": {"poll_interval_seconds": 600, "history_limit": 50},
        "subscriptions": [
            {"id": "news/rss-generic", "parameters": {"url": "https://example.com/a.xml"}},
            {"id": "news/rss-generic", "parameters": {"url": "https://example.com/b.xml"}},
        ],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "subscriptions.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert cli.main(["--root", str(tmp_path), "unsubscribe", "news/rss-generic"]) == 2
