from __future__ import annotations

import json
from pathlib import Path
import sys
import textwrap

import agentfeeds_runtime.adapters.http as http_adapter
import agentfeeds_runtime.adapters.ical as ical_adapter
import agentfeeds_runtime.fetcher as fetcher

ROOT = Path(__file__).resolve().parents[1]


def test_state_path_for_stream_matches_spec_examples(tmp_path):
    weather_path = fetcher.state_path_for_stream(
        "feed://weather.gov/forecast?lat=37.33&lon=-121.89",
        tmp_path,
    )
    assert weather_path.parent == tmp_path / "state" / "weather.gov"
    assert weather_path.name.startswith("forecast.lat-37.33-lon--121.89.")
    assert weather_path.name.endswith(".json")

    assert fetcher.state_path_for_stream(
        "feed://github.com/repos/anthropics/claude-code/releases",
        tmp_path,
    ) == tmp_path / "state" / "github.com" / "repos.anthropics.claude-code.releases.json"


def test_state_path_for_stream_sanitizes_url_parameters_to_flat_filename(tmp_path):
    state_path = fetcher.state_path_for_stream(
        "feed://calendar.local/ics?url=https://example.com/calendar.ics",
        tmp_path,
    )

    assert state_path.parent == tmp_path / "state" / "calendar.local"
    assert state_path.name.startswith("ics.url-https-example.com-calendar.ics.")
    assert state_path.name.endswith(".json")


def test_atomic_write_json_writes_complete_file(tmp_path):
    target = tmp_path / "state" / "example.com" / "stream.json"

    fetcher.atomic_write_json(target, {"ok": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
    assert not target.with_suffix(".json.tmp").exists()


def test_fetch_lock_skips_overlapping_run(tmp_path, capsys):
    fetcher.ensure_root(tmp_path)
    with fetcher.fetch_lock(tmp_path) as acquired:
        assert acquired is True
        assert fetcher.main(["--root", str(tmp_path), "--all"]) == 1

    err = capsys.readouterr().err
    assert "already running" in err


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
                template: weather/openmeteo-current
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

    monkeypatch.setattr(http_adapter.requests, "request", lambda *args, **kwargs: FakeResponse())

    assert fetcher.main(["--root", str(tmp_path), "--once", "weather/santa-clara-current"]) == 0

    state_path = fetcher.state_path_for_stream(
        "feed://api.open-meteo.com/v1/forecast?latitude=37.33&longitude=-121.89",
        tmp_path,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["_meta"]["subscription_id"] == "weather/santa-clara-current"
    assert state["_meta"]["template_id"] == "weather/openmeteo-current"
    assert state["_meta"]["title"] == "Santa Clara current weather"
    assert state["_meta"]["stale"] is False
    assert state["data"]["temperature_c"] == 22.1
    status = fetcher.load_fetch_status(tmp_path, "weather/santa-clara-current")
    assert status["subscription_id"] == "weather/santa-clara-current"
    assert status["last_success_at"]
    assert status["last_error"] is None
    assert status["consecutive_failures"] == 0
    assert status["state_path"] == str(state_path.relative_to(tmp_path))
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

    subscription = {"id": "dev/example-instance", "title": "Example instance", "template": "dev/example"}
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
                template: local/file
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
    assert state["_meta"]["template_id"] == "local/file"
    assert state["data"]["path"] == str(source)
    assert state["data"]["name"] == "notes.md"
    assert state["data"]["content"] == "# Notes\n\nLocal context.\n"
    assert len(state["data"]["sha256"]) == 64


def test_fetch_failure_writes_status(tmp_path, capsys):
    agentfeeds_root = tmp_path / "agentfeeds"
    missing = tmp_path / "missing.md"
    agentfeeds_root.mkdir()
    (agentfeeds_root / "subscriptions.yaml").write_text(
        textwrap.dedent(
            f"""
            version: "0.3"
            defaults:
              poll_interval_seconds: 600
              history_limit: 50
            subscriptions:
              - id: local/missing-md
                title: missing.md
                template: local/file
                parameters:
                  path: {missing}
            """
        ),
        encoding="utf-8",
    )

    assert fetcher.main(["--root", str(agentfeeds_root), "--once", "local/missing-md"]) == 1
    assert "local/missing-md" in capsys.readouterr().err

    status = fetcher.load_fetch_status(agentfeeds_root, "local/missing-md")
    assert status["subscription_id"] == "local/missing-md"
    assert status["last_attempt_at"]
    assert status["last_success_at"] is None
    assert status["last_error_at"]
    assert "local file not found" in status["last_error"]
    assert status["consecutive_failures"] == 1


def test_fetch_status_redacts_sensitive_error_text(tmp_path):
    fetcher.ensure_root(tmp_path)
    fetcher.write_fetch_status(
        tmp_path,
        {"id": "dev/private", "template": "dev/private"},
        None,
        attempted_at="2026-05-03T12:00:00Z",
        succeeded=False,
        error="Authorization: Bearer abc123 token=xyz cookie=session",
    )

    status = fetcher.load_fetch_status(tmp_path, "dev/private")
    assert "abc123" not in status["last_error"]
    assert "xyz" not in status["last_error"]
    assert "[redacted]" in status["last_error"]


def _approve_local_command(root: Path, stream: dict, parameters: dict | None = None) -> None:
    adapter = fetcher.substitute(stream["adapter"], parameters or {})
    fetcher.write_local_command_approval(root, stream, adapter)


def test_local_command_fetch_requires_approval(tmp_path):
    stream = {
        "id": "personal/command",
        "title": "Command",
        "description": "Command snapshot",
        "type": "local.command",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/local.command.v1.json",
        "schema_version": "1.0.0",
        "source_uri_template": "feed://personal.command/command",
        "adapter": {
            "kind": "local_command",
            "command": [sys.executable, "-c", "print('hello from command')"],
        },
    }

    try:
        fetcher.run_adapter(stream, {}, tmp_path)
    except PermissionError as exc:
        assert "local_command is not approved" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected approval failure")


def test_local_command_fetch_refuses_pending_template(tmp_path):
    stream = {
        "id": "personal/command",
        "title": "Command",
        "description": "Command snapshot",
        "type": "local.command",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/local.command.v1.json",
        "schema_version": "1.0.0",
        "source_uri_template": "feed://personal.command/command",
        "pending": True,
        "adapter": {
            "kind": "local_command",
            "command": [sys.executable, "-c", "print('hello from command')"],
        },
    }

    _approve_local_command(tmp_path, stream)
    try:
        fetcher.run_adapter(stream, {}, tmp_path)
    except PermissionError as exc:
        assert "pending operator approval" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected pending-template failure")


def test_local_command_fetch_writes_stdout_snapshot(tmp_path):
    stream = {
        "id": "personal/command",
        "title": "Command",
        "description": "Command snapshot",
        "type": "local.command",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/local.command.v1.json",
        "schema_version": "1.0.0",
        "source_uri_template": "feed://personal.command/command",
        "adapter": {
            "kind": "local_command",
            "command": [sys.executable, "-c", "print('hello from command')"],
        },
    }

    _approve_local_command(tmp_path, stream)
    stream_uri, events = fetcher.run_adapter(stream, {}, tmp_path)

    assert stream_uri == "feed://personal.command/command"
    assert len(events) == 1
    assert events[0]["data"]["exit_code"] == 0
    assert events[0]["data"]["stdout"] == "hello from command\n"
    assert events[0]["data"]["stderr"] == ""
    assert events[0]["data"]["parsed_json"] is None
    assert events[0]["data"]["transformed"] is None


def test_secret_refs_resolve_before_http_adapter_runs(tmp_path, monkeypatch):
    fetcher.ensure_root(tmp_path)
    fetcher.write_secret(tmp_path, "api_token", "secret-value")
    stream = {
        "id": "dev/private",
        "title": "Private API",
        "description": "Private API",
        "type": "dev.private",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/dev.private.v1.json",
        "schema_version": "1.0.0",
        "parameters": [],
        "source_uri_template": "feed://dev.private/api",
        "adapter": {
            "kind": "json_http",
            "url": "https://api.example.test/private",
            "method": "GET",
            "headers": {"Authorization": "Bearer {{secret:api_token}}"},
            "transform": {"language": "jmespath", "expression": "{title: title}"},
        },
    }
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"title": "Private"}

    def fake_request(_method, _url, **kwargs):
        seen["headers"] = kwargs.get("headers")
        return FakeResponse()

    monkeypatch.setattr(http_adapter.requests, "request", fake_request)

    _stream_uri, events = fetcher.run_adapter(stream, {}, tmp_path)

    assert seen["headers"]["Authorization"] == "Bearer secret-value"
    assert events[0]["data"] == {"title": "Private"}


def test_local_command_fetch_can_parse_json_and_transform(tmp_path):
    stream = {
        "id": "personal/json-command",
        "title": "JSON command",
        "description": "JSON command snapshot",
        "type": "local.command",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/local.command.v1.json",
        "schema_version": "1.0.0",
        "source_uri_template": "feed://personal.command/json",
        "adapter": {
            "kind": "local_command",
            "command": [
                sys.executable,
                "-c",
                "import json; print(json.dumps({'items': [{'title': 'A'}, {'title': 'B'}]}))",
            ],
            "parse": "json",
            "transform": {
                "language": "jmespath",
                "expression": "items[].title",
            },
        },
    }

    _approve_local_command(tmp_path, stream)
    _stream_uri, events = fetcher.run_adapter(stream, {}, tmp_path)

    data = events[0]["data"]
    assert data["exit_code"] == 0
    assert data["parsed_json"] == {"items": [{"title": "A"}, {"title": "B"}]}
    assert data["transformed"] == ["A", "B"]


def test_local_command_fetch_event_mode_emits_one_event_per_item(tmp_path):
    stream = {
        "id": "personal/recent-items",
        "title": "Recent items",
        "description": "Recent items from a local command",
        "type": "personal.item",
        "mode": "event",
        "schema_url": "https://agentfeeds.dev/schemas/personal.item.v1.json",
        "schema_version": "1.0.0",
        "source_uri_template": "feed://personal.command/recent-items",
        "adapter": {
            "kind": "local_command",
            "command": [
                sys.executable,
                "-c",
                (
                    "import json; "
                    "print(json.dumps({'items': ["
                    "{'id': 'a', 'title': 'A', 'summary': 'Alpha', 'updated_at': '2026-05-01T00:00:00Z'}, "
                    "{'id': 'b', 'title': 'B', 'summary': 'Beta', 'updated_at': '2026-05-01T01:00:00Z'}"
                    "]}))"
                ),
            ],
            "parse": "json",
            "items_from": "items",
            "id_from": "id",
            "time_from": "updated_at",
            "transform": {
                "language": "jmespath",
                "expression": "{title: title, content: summary, updated_at: updated_at}",
            },
        },
    }

    _approve_local_command(tmp_path, stream)
    _stream_uri, events = fetcher.run_adapter(stream, {}, tmp_path)

    assert [event["id"] for event in events] == ["a", "b"]
    assert [event["time"] for event in events] == ["2026-05-01T00:00:00Z", "2026-05-01T01:00:00Z"]
    assert events[0]["data"] == {
        "title": "A",
        "content": "Alpha",
        "updated_at": "2026-05-01T00:00:00Z",
    }
    assert "stdout" not in events[0]["data"]


def test_github_issue_and_pr_adapters_transform_payloads(tmp_path, monkeypatch):
    issues = fetcher.load_stream_definition(tmp_path, "dev/github-issues")
    prs = fetcher.load_stream_definition(tmp_path, "dev/github-prs")

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_request(_method, url, **_kwargs):
        if "/issues" in url:
            return FakeResponse(
                [
                    {
                        "number": 1,
                        "title": "Issue one",
                        "state": "open",
                        "html_url": "https://github.com/example/repo/issues/1",
                        "user": {"login": "alice"},
                        "labels": [{"name": "bug"}],
                        "created_at": "2026-05-01T00:00:00Z",
                        "updated_at": "2026-05-01T01:00:00Z",
                        "closed_at": None,
                        "body": "body",
                    },
                    {
                        "number": 2,
                        "title": "PR in issues API",
                        "pull_request": {},
                    },
                ]
            )
        return FakeResponse(
            [
                {
                    "number": 3,
                    "title": "PR one",
                    "state": "open",
                    "html_url": "https://github.com/example/repo/pull/3",
                    "user": {"login": "bob"},
                    "draft": False,
                    "head": {"ref": "feature"},
                    "base": {"ref": "main"},
                    "created_at": "2026-05-01T00:00:00Z",
                    "updated_at": "2026-05-01T01:00:00Z",
                    "closed_at": None,
                    "merged_at": None,
                    "body": "body",
                }
            ]
        )

    monkeypatch.setattr(http_adapter.requests, "request", fake_request)

    _issues_uri, issue_events = fetcher.run_adapter(issues, {"owner": "example", "repo": "repo", "state": "open"})
    _prs_uri, pr_events = fetcher.run_adapter(prs, {"owner": "example", "repo": "repo", "state": "open"})

    assert len(issue_events) == 1
    assert issue_events[0]["id"] == "1"
    assert issue_events[0]["data"]["labels"] == ["bug"]
    assert len(pr_events) == 1
    assert pr_events[0]["id"] == "3"
    assert pr_events[0]["data"]["head_ref"] == "feature"


def test_calendar_ics_fetch_writes_event_state(tmp_path, monkeypatch):
    (tmp_path / "subscriptions.yaml").write_text(
        textwrap.dedent(
            """
            version: "0.3"
            defaults:
              poll_interval_seconds: 600
              history_limit: 50
            subscriptions:
              - id: calendar/example-com
                title: Example calendar
                template: calendar/ics
                parameters:
                  url: https://example.com/calendar.ics
            """
        ),
        encoding="utf-8",
    )

    class FakeResponse:
        content = textwrap.dedent(
            """
            BEGIN:VCALENDAR
            VERSION:2.0
            BEGIN:VEVENT
            UID:event-1
            SUMMARY:Example event
            DTSTART:20260502T120000Z
            DTEND:20260502T130000Z
            LOCATION:Online
            END:VEVENT
            END:VCALENDAR
            """
        ).strip().encode("utf-8")

        def raise_for_status(self):
            return None

    monkeypatch.setattr(ical_adapter.requests, "get", lambda *_args, **_kwargs: FakeResponse())

    assert fetcher.main(["--root", str(tmp_path), "--once", "calendar/example-com"]) == 0

    state_path = fetcher.state_path_for_stream(
        "feed://calendar.local/ics?url=https://example.com/calendar.ics",
        tmp_path,
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["_meta"]["subscription_id"] == "calendar/example-com"
    assert state["_meta"]["template_id"] == "calendar/ics"
    assert state["data"][0]["data"]["summary"] == "Example event"
