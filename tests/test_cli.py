from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

import agentfeeds.commands as cli


def test_cli_subscribe_streams_and_unsubscribe_without_fetch(tmp_path, capsys):
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
            "template": "weather/openmeteo-current",
            "parameters": {"lat": 37.3541, "lon": -121.9552},
        }
    ]
    capsys.readouterr()

    assert cli.main(["--root", str(tmp_path), "streams", "list", "--json"]) == 0
    streams = json.loads(capsys.readouterr().out)
    assert streams["streams"][0]["id"] == "weather/santa-clara-current"
    assert streams["streams"][0]["template"] == "weather/openmeteo-current"
    assert streams["streams"][0]["exists"] is False

    assert cli.main([
        "--root",
        str(tmp_path),
        "unsubscribe",
        "weather/santa-clara-current",
    ]) == 0
    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == []


def test_cli_templates_search_filters_catalog(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "templates", "search", "hacker"]) == 0
    out = capsys.readouterr().out
    assert "dev/hackernews-frontpage" in out
    assert "weather/openmeteo-current" not in out


def test_cli_templates_show_catalog_entry(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "templates", "search", "hacker"]) == 0
    out = capsys.readouterr().out
    assert "dev/hackernews-frontpage" in out

    assert cli.main(["--root", str(tmp_path), "templates", "show", "local/file", "--json"]) == 0
    template = json.loads(capsys.readouterr().out)
    assert template["id"] == "local/file"
    assert template["parameters"][0]["name"] == "path"


def test_cli_materializes_parameterized_subscription(tmp_path, monkeypatch):
    class Parsed:
        feed = {"title": "Example News"}
        entries = [{"link": "https://example.com/a"}, {"link": "https://example.com/b"}]

    class FakeResponse:
        content = b"<rss />"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(cli.requests, "get", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(cli.feedparser, "parse", lambda *_args, **_kwargs: Parsed())

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
            "template": "news/rss-generic",
            "parameters": {"url": "https://feeds.example.net/rss.xml"},
        }
    ]


def test_cli_keeps_no_parameter_template_identity(tmp_path):
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
            "template": "dev/hackernews-frontpage",
        }
    ]

    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "dev/hackernews-frontpage",
        "--no-fetch",
    ]) == 2


def test_cli_materializes_local_file_subscription(tmp_path):
    source = tmp_path / "Project Notes.md"
    source.write_text("# Project Notes\n", encoding="utf-8")

    assert cli.main([
        "--root",
        str(tmp_path / "agentfeeds"),
        "subscribe",
        "local/file",
        f"path={source}",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "agentfeeds" / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"] == [
        {
            "id": "local/project-notes-md",
            "title": "Project Notes.md",
            "template": "local/file",
            "parameters": {"path": str(source)},
        }
    ]


def test_cli_streams_list_search_show_and_read(tmp_path, capsys):
    source = tmp_path / "Project Notes.md"
    source.write_text("# Project Notes\n\nLocal context.\n", encoding="utf-8")
    root = tmp_path / "agentfeeds"

    assert cli.main([
        "--root",
        str(root),
        "subscribe",
        "local/file",
        f"path={source}",
    ]) == 0
    capsys.readouterr()

    assert cli.main(["--root", str(root), "streams", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["streams"][0]["id"] == "local/project-notes-md"

    assert cli.main(["--root", str(root), "streams", "search", "project", "--json"]) == 0
    searched = json.loads(capsys.readouterr().out)
    assert searched["streams"][0]["id"] == "local/project-notes-md"

    assert cli.main(["--root", str(root), "streams", "show", "local/project-notes-md", "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["template"] == "local/file"
    assert shown["exists"] is True
    assert shown["data_summary"]["keys"]

    assert cli.main(["--root", str(root), "streams", "read", "local/project-notes-md", "--json"]) == 0
    read = json.loads(capsys.readouterr().out)
    assert read["template"] == "local/file"
    assert read["data"]["content"] == "# Project Notes\n\nLocal context.\n"


def test_cli_template_helpers(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "templates", "path"]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path / "templates")

    assert cli.main(["--root", str(tmp_path), "templates", "validate"]) == 0
    assert "No local templates found" in capsys.readouterr().out

    assert cli.main(["--root", str(tmp_path), "templates", "list"]) == 0
    out = capsys.readouterr().out
    assert "local/file: Local file" in out
    assert "source: builtin" in out

    assert cli.main(["--root", str(tmp_path), "templates", "adapters"]) == 0
    out = capsys.readouterr().out
    assert "local_file:" in out
    assert "local_command:" in out
    assert "json_http:" in out


def test_cli_scaffolds_local_template(tmp_path, capsys):
    assert cli.main([
        "--root",
        str(tmp_path),
        "templates",
        "scaffold",
        "json_http",
        "personal/tasks",
    ]) == 0

    stream_path = tmp_path / "templates" / "streams" / "personal" / "tasks.yaml"
    schema_path = tmp_path / "templates" / "schemas" / "event-types" / "personal.tasks.v1.json"
    stream = yaml.safe_load(stream_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert stream["id"] == "personal/tasks"
    assert stream["adapter"]["kind"] == "json_http"
    assert stream["parameters"][0]["name"] == "url"
    assert schema["$id"] == "https://agentfeeds.dev/schemas/personal.tasks.v1.json"
    assert "wrote:" in capsys.readouterr().out
    assert cli.main(["--root", str(tmp_path), "templates", "validate"]) == 0


def test_cli_scaffold_reuses_builtin_schema_for_rss(tmp_path):
    assert cli.main([
        "--root",
        str(tmp_path),
        "templates",
        "scaffold",
        "rss",
        "news/example",
    ]) == 0

    stream_path = tmp_path / "templates" / "streams" / "news" / "example.yaml"
    stream = yaml.safe_load(stream_path.read_text(encoding="utf-8"))

    assert stream["type"] == "rss.item"
    assert stream["schema_url"] == "https://agentfeeds.dev/schemas/rss-item.v1.json"
    assert not (tmp_path / "templates" / "schemas" / "event-types" / "news.example.v1.json").exists()


def test_cli_scaffold_reuses_builtin_schema_for_local_command(tmp_path):
    assert cli.main([
        "--root",
        str(tmp_path),
        "templates",
        "scaffold",
        "local_command",
        "personal/command",
    ]) == 0

    stream_path = tmp_path / "templates" / "streams" / "personal" / "command.yaml"
    stream = yaml.safe_load(stream_path.read_text(encoding="utf-8"))

    assert stream["id"] == "personal/command"
    assert stream["mode"] == "snapshot"
    assert stream["type"] == "local.command"
    assert stream["schema_url"] == "https://agentfeeds.dev/schemas/local.command.v1.json"
    assert stream["adapter"]["kind"] == "local_command"
    assert stream["adapter"]["parse"] == "json"
    assert stream["adapter"]["transform"]["language"] == "jmespath"
    assert not (tmp_path / "templates" / "schemas" / "event-types" / "personal.command.v1.json").exists()
    assert cli.main(["--root", str(tmp_path), "templates", "validate"]) == 0


def test_cli_template_test_runs_template_without_writing_state(tmp_path, capsys):
    source = tmp_path / "Project Notes.md"
    source.write_text("# Project Notes\n", encoding="utf-8")

    assert cli.main([
        "--root",
        str(tmp_path / "agentfeeds"),
        "templates",
        "test",
        "local/file",
        f"path={source}",
        "--json",
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["template"] == "local/file"
    assert result["mode"] == "snapshot"
    assert result["event_count"] == 1
    assert result["sample"]["content"] == "# Project Notes\n"
    assert result["state_path"].startswith("state/local.file/file.Project-Notes.md.")
    assert not (tmp_path / "agentfeeds" / "state" / "local.file").exists()


def test_cli_template_test_supports_event_command_without_items_from(tmp_path, capsys):
    streams_root = tmp_path / "templates" / "streams" / "personal"
    schemas_root = tmp_path / "templates" / "schemas" / "event-types"
    streams_root.mkdir(parents=True)
    schemas_root.mkdir(parents=True)
    (schemas_root / "personal.item.v1.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://agentfeeds.dev/schemas/personal.item.v1.json",
                "title": "Personal item",
                "type": "object",
                "properties": {"title": {"type": "string"}},
            }
        ),
        encoding="utf-8",
    )
    (streams_root / "items.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "personal/items",
                "title": "Personal items",
                "description": "Recent personal items",
                "type": "personal.item",
                "mode": "event",
                "schema_url": "https://agentfeeds.dev/schemas/personal.item.v1.json",
                "schema_version": "1.0.0",
                "parameters": [],
                "source_uri_template": "feed://personal.items/recent",
                "adapter": {
                    "kind": "local_command",
                    "command": [
                        sys.executable,
                        "-c",
                        "import json; print(json.dumps([{'id': 'one', 'title': 'One'}]))",
                    ],
                    "parse": "json",
                    "id_from": "id",
                    "transform": {
                        "language": "jmespath",
                        "expression": "{title: title}",
                    },
                },
                "recommended_poll_interval_seconds": 300,
                "auth": "none",
                "tags": ["personal"],
                "quality_tier": "experimental",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert cli.main([
        "--root",
        str(tmp_path),
        "templates",
        "test",
        "personal/items",
        "--json",
    ]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["template"] == "personal/items"
    assert result["mode"] == "event"
    assert result["event_count"] == 1
    assert result["sample"] == {"title": "One"}


def test_cli_materializes_github_issue_and_pr_subscriptions(tmp_path):
    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "dev/github-issues",
        "owner=NousResearch",
        "repo=hermes-agent",
        "state=open",
        "--no-fetch",
    ]) == 0
    assert cli.main([
        "--root",
        str(tmp_path),
        "subscribe",
        "dev/github-prs",
        "owner=NousResearch",
        "repo=hermes-agent",
        "state=open",
        "--no-fetch",
    ]) == 0

    config = yaml.safe_load((tmp_path / "subscriptions.yaml").read_text(encoding="utf-8"))
    assert config["subscriptions"][0]["id"] == "dev/nousresearch-hermes-agent-issues"
    assert config["subscriptions"][0]["title"] == "NousResearch/hermes-agent issues"
    assert config["subscriptions"][1]["id"] == "dev/nousresearch-hermes-agent-prs"
    assert config["subscriptions"][1]["title"] == "NousResearch/hermes-agent prs"
