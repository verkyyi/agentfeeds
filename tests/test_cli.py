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
        "--id",
        "weather/santa-clara-current",
        "--title",
        "Santa Clara current weather",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == [
        {
            "id": "weather/santa-clara-current",
            "title": "Santa Clara current weather",
            "provider": "weather/openmeteo-current",
            "parameters": {"lat": 37.3541, "lon": -121.9552},
        }
    ]

    assert cli.main(["--root", str(tmp_path), "status", "--json"]) == 0
    status_out = capsys.readouterr().out
    status = json.loads(status_out[status_out.index("{"):])
    assert status["subscriptions"][0]["id"] == "weather/santa-clara-current"
    assert status["subscriptions"][0]["provider"] == "weather/openmeteo-current"
    assert status["subscriptions"][0]["exists"] is False

    assert cli.main([
        "--root",
        str(tmp_path),
        "unsubscribe",
        "weather/santa-clara-current",
    ]) == 0
    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == []


def test_cli_discover_filters_catalog(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "discover", "hacker"]) == 0
    out = capsys.readouterr().out
    assert "dev/hackernews-frontpage" in out
    assert "weather/openmeteo-current" not in out


def test_cli_materializes_parameterized_subscription(tmp_path, monkeypatch):
    class Parsed:
        feed = {"title": "Example News"}
        entries = [{"link": "https://example.com/a"}, {"link": "https://example.com/b"}]

    class FakeResponse:
        content = b"<rss />"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(cli.fetch.requests, "get", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(cli.fetch.feedparser, "parse", lambda *_args, **_kwargs: Parsed())

    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "news/rss-generic",
        "url=https://feeds.example.net/rss.xml",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == [
        {
            "id": "news/example-com",
            "title": "Example News",
            "provider": "news/rss-generic",
            "parameters": {"url": "https://feeds.example.net/rss.xml"},
        }
    ]


def test_cli_keeps_no_parameter_provider_identity(tmp_path):
    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "dev/hackernews-frontpage",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == [
        {
            "id": "dev/hackernews-frontpage",
            "title": "Hacker News front page",
            "provider": "dev/hackernews-frontpage",
        }
    ]

    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "dev/hackernews-frontpage",
        "--no-fetch",
    ]) == 2
