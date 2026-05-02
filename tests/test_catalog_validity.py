from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from agentfeeds import fetch


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-stream.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_stream", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_all_streams_validate():
    validator = load_validator()
    for path in sorted((ROOT / "catalog" / "streams").glob("**/*.yaml")):
        validator.validate_stream(path)


def test_index_matches_stream_count():
    index = json.loads((ROOT / "catalog" / "INDEX.json").read_text(encoding="utf-8"))
    streams = sorted((ROOT / "catalog" / "streams").glob("**/*.yaml"))
    assert index["stream_count"] == len(streams)


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
