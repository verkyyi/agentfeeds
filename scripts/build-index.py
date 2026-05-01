#!/usr/bin/env python3
"""Build catalog/INDEX.json from catalog/streams/**/*.yaml."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
STREAMS_ROOT = ROOT / "catalog" / "streams"
INDEX_PATH = ROOT / "catalog" / "INDEX.json"


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stream_summary(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "id": data["id"],
        "title": data["title"],
        "description": data["description"],
        "type": data["type"],
        "mode": data["mode"],
        "tags": data.get("tags", []),
        "parameters": [param["name"] for param in data.get("parameters", [])],
        "auth": data["auth"],
        "quality_tier": data["quality_tier"],
        "path": str(path.relative_to(ROOT)),
    }


def build_index() -> dict:
    streams = [stream_summary(path) for path in sorted(STREAMS_ROOT.glob("**/*.yaml"))]
    return {
        "generated_at": now_utc(),
        "spec_version": "0.3",
        "stream_count": len(streams),
        "streams": streams,
    }


def main() -> int:
    payload = build_index()
    INDEX_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {INDEX_PATH} with {payload['stream_count']} streams")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
