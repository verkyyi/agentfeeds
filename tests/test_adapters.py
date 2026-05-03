from __future__ import annotations

from agentfeeds_runtime.adapters.local_command import _decode_limited
from agentfeeds_runtime.adapters.local_file import fetch_local_file


def test_local_file_adapter_emits_snapshot_envelope(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("local context\n", encoding="utf-8")
    stream = {
        "id": "local/file",
        "type": "local.file",
        "mode": "snapshot",
        "schema_url": "https://agentfeeds.dev/schemas/local.file.v1.json",
        "schema_version": "1.0.0",
    }

    events = fetch_local_file(stream, {"path": str(source)}, "feed://local.file/file")

    assert len(events) == 1
    assert events[0]["source"] == "feed://local.file/file"
    assert events[0]["data"]["name"] == "notes.md"
    assert events[0]["data"]["content"] == "local context\n"
    assert len(events[0]["data"]["sha256"]) == 64


def test_decode_limited_reports_truncation():
    text, truncated = _decode_limited("abcdef".encode("utf-8"), 3)

    assert text == "abc"
    assert truncated is True
