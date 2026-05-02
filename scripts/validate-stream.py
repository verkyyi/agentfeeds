#!/usr/bin/env python3
"""Validate one Agent Feeds stream definition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
STREAM_SCHEMA = ROOT / "catalog" / "schemas" / "stream-definition.v0.3.json"
EVENT_SCHEMAS = ROOT / "catalog" / "schemas" / "event-types"


def schema_path_for_url(schema_url: str) -> Path:
    name = schema_url.rstrip("/").split("/")[-1]
    path = EVENT_SCHEMAS / name
    if path.exists():
        return path
    raise FileNotFoundError(f"referenced schema not found locally: {schema_url}")


def validate_stream(path: Path) -> None:
    stream = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = json.loads(STREAM_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(stream, schema)

    schema_path = schema_path_for_url(stream["schema_url"])
    json.loads(schema_path.read_text(encoding="utf-8"))

    adapter_kind = stream["adapter"]["kind"]
    if adapter_kind in {"json_http", "paginated_json_http"}:
        for required in ("url", "method", "transform"):
            if required not in stream["adapter"]:
                raise ValueError(f"{path}: adapter.{required} is required for {adapter_kind}")
    if adapter_kind in {"rss", "ical"} and "url" not in stream["adapter"]:
        raise ValueError(f"{path}: adapter.url is required for {adapter_kind}")
    if adapter_kind == "local_file" and "path" not in stream["adapter"]:
        raise ValueError(f"{path}: adapter.path is required for local_file")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream", type=Path)
    args = parser.parse_args()
    validate_stream(args.stream)
    print(f"valid: {args.stream}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
