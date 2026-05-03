import json
from pathlib import Path

import yaml

from agentfeeds import fetch


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CATALOG = ROOT / "tests" / "fixtures" / "catalog"


def test_catalog_cache_updates_from_configured_catalog_dir(tmp_path):
    fetch.update_catalog_cache(tmp_path)

    index = json.loads((tmp_path / "catalog-cache" / "INDEX.json").read_text(encoding="utf-8"))
    assert index["stream_count"] == 7
    assert (tmp_path / "catalog-cache" / "catalog" / "streams" / "local" / "file.yaml").exists()
    assert (
        tmp_path
        / "catalog-cache"
        / "catalog"
        / "schemas"
        / "event-types"
        / "local.file.v1.json"
    ).exists()


def test_catalog_cache_can_download_remote_catalog(tmp_path, monkeypatch):
    files = {
        str(path.relative_to(FIXTURE_CATALOG)): path.read_text(encoding="utf-8")
        for path in (FIXTURE_CATALOG / "catalog").glob("**/*")
        if path.is_file()
    }

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(url: str, **_kwargs):
        relative_path = url.removeprefix("https://catalog.example/")
        if relative_path not in files:
            raise AssertionError(f"unexpected catalog URL: {url}")
        return FakeResponse(files[relative_path])

    monkeypatch.delenv("AGENTFEEDS_CATALOG_DIR", raising=False)
    monkeypatch.setenv("AGENTFEEDS_CATALOG_BASE_URL", "https://catalog.example")
    monkeypatch.setattr(fetch.requests, "get", fake_get)

    fetch.update_catalog_cache(tmp_path)

    assert (tmp_path / "catalog-cache" / "catalog" / "streams" / "calendar" / "ics.yaml").exists()
    assert (
        tmp_path
        / "catalog-cache"
        / "catalog"
        / "schemas"
        / "event-types"
        / "ical-event.v1.json"
    ).exists()


def test_load_stream_definition_uses_catalog_cache(tmp_path):
    stream = fetch.load_stream_definition(tmp_path, "local/file")

    assert stream["id"] == "local/file"
    assert stream["adapter"]["kind"] == "local_file"


def test_local_provider_is_discoverable_and_validates(tmp_path):
    stream_dir = tmp_path / "providers" / "streams" / "personal"
    schema_dir = tmp_path / "providers" / "schemas" / "event-types"
    stream_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    (schema_dir / "personal.note.v1.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://agentfeeds.dev/schemas/personal.note.v1.json",
                "title": "Personal Note",
                "type": "object",
                "required": ["content"],
                "properties": {"content": {"type": "string"}},
            }
        ),
        encoding="utf-8",
    )
    (stream_dir / "note.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "personal/note",
                "title": "Personal note",
                "description": "Read-only test provider.",
                "type": "personal.note",
                "mode": "snapshot",
                "schema_url": "https://agentfeeds.dev/schemas/personal.note.v1.json",
                "schema_version": "1.0.0",
                "parameters": [
                    {
                        "name": "path",
                        "type": "string",
                        "description": "File path",
                        "required": True,
                    }
                ],
                "source_uri_template": "feed://personal.note/source?path={path}",
                "adapter": {"kind": "local_file", "path": "{path}"},
                "recommended_poll_interval_seconds": 300,
                "auth": "none",
                "tags": ["personal", "local"],
                "quality_tier": "verified",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    fetch.ensure_root(tmp_path)
    index = fetch.load_catalog_index(tmp_path)
    provider = next(stream for stream in index["streams"] if stream["id"] == "personal/note")

    assert provider["source"] == "local"
    assert provider["parameters"] == ["path"]
    assert fetch.validate_provider_tree(tmp_path) == [stream_dir / "note.yaml"]


def test_local_provider_cannot_override_builtin(tmp_path):
    stream_dir = tmp_path / "providers" / "streams" / "local"
    stream_dir.mkdir(parents=True)
    (stream_dir / "file.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "local/file",
                "title": "Overridden file",
                "description": "Conflicting provider.",
                "type": "local.file",
                "mode": "snapshot",
                "schema_url": "https://agentfeeds.dev/schemas/local.file.v1.json",
                "schema_version": "1.0.0",
                "parameters": [],
                "source_uri_template": "feed://local.file/conflict",
                "adapter": {"kind": "local_file", "path": "{path}"},
                "recommended_poll_interval_seconds": 300,
                "auth": "none",
                "tags": ["local"],
                "quality_tier": "verified",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    fetch.ensure_root(tmp_path)
    index = fetch.load_catalog_index(tmp_path)
    provider = next(stream for stream in index["streams"] if stream["id"] == "local/file")

    assert provider["title"] == "Local file"
    try:
        fetch.validate_provider_tree(tmp_path)
    except ValueError as exc:
        assert "conflicts with built-in provider" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected duplicate provider validation failure")
