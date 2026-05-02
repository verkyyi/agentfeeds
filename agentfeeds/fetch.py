#!/usr/bin/env python3
"""Reference fetcher for Agent Feeds v0.3."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import feedparser
import icalendar
import jmespath
import jsonschema
import requests

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


SPEC_VERSION = "0.3"
AGENTFEEDS_VERSION = "agentfeeds/0.3"
DEFAULT_ROOT = Path.home() / ".agentfeeds"
REQUEST_TIMEOUT_SECONDS = 20
PARAMETER_PATTERN = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def state_path_for_stream(stream_uri: str, root: Path = DEFAULT_ROOT) -> Path:
    parsed = urlparse(stream_uri)
    if parsed.scheme != "feed" or not parsed.netloc:
        raise ValueError(f"invalid feed URI: {stream_uri}")

    path = parsed.path.lstrip("/").replace("/", ".")
    name = path or "index"
    if parsed.netloc == "local.file":
        params = parse_qs(parsed.query, keep_blank_values=True)
        local_path = (params.get("path") or [""])[0]
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(local_path).name).strip("-") or "file"
        digest = hashlib.sha256(parsed.query.encode("utf-8")).hexdigest()[:12]
        return root / "state" / parsed.netloc / f"{name}.{stem}.{digest}.json"
    if parsed.query:
        name = f"{name}.{parsed.query.replace('&', ',')}"
    return root / "state" / parsed.netloc / f"{name}.json"


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def ensure_root(root: Path) -> None:
    (root / "catalog-cache").mkdir(parents=True, exist_ok=True)
    (root / "state").mkdir(parents=True, exist_ok=True)
    (root / "providers" / "streams").mkdir(parents=True, exist_ok=True)
    (root / "providers" / "schemas" / "event-types").mkdir(parents=True, exist_ok=True)
    subscriptions = root / "subscriptions.yaml"
    if not subscriptions.exists():
        subscriptions.write_text(
            'version: "0.3"\n'
            "defaults:\n"
            "  poll_interval_seconds: 600\n"
            "  history_limit: 50\n"
            "subscriptions: []\n",
            encoding="utf-8",
        )


def load_subscriptions(root: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read subscriptions.yaml")
    path = root / "subscriptions.yaml"
    if not path.exists():
        return {"version": SPEC_VERSION, "subscriptions": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def providers_root(root: Path) -> Path:
    return root / "providers"


def provider_streams_root(root: Path) -> Path:
    return providers_root(root) / "streams"


def provider_schemas_root(root: Path) -> Path:
    return providers_root(root) / "schemas" / "event-types"


def builtin_event_schemas_root() -> Path:
    return repo_root() / "catalog" / "schemas" / "event-types"


def update_catalog_cache(root: Path) -> None:
    source = repo_root() / "catalog" / "INDEX.json"
    if not source.exists():
        raise FileNotFoundError(f"catalog index not found: {source}")
    target = root / "catalog-cache" / "INDEX.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def load_catalog_index(root: Path) -> dict:
    cache = root / "catalog-cache" / "INDEX.json"
    if not cache.exists():
        update_catalog_cache(root)
    index = json.loads(cache.read_text(encoding="utf-8"))
    streams = {stream["id"]: {**stream, "source": stream.get("source") or "builtin"} for stream in index.get("streams", [])}
    for path in sorted(provider_streams_root(root).glob("**/*.yaml")):
        stream = stream_summary(path, root)
        if stream["id"] in streams:
            continue
        streams[stream["id"]] = stream
    merged = {**index, "streams": sorted(streams.values(), key=lambda item: item["id"])}
    merged["stream_count"] = len(merged["streams"])
    return merged


def stream_summary(path: Path, root: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        rel_path = str(path.relative_to(repo_root()))
        source = "builtin"
    except ValueError:
        rel_path = str(path)
        source = "local"
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
        "path": rel_path,
        "source": source,
    }


def load_stream_definition(root: Path, stream_id: str) -> dict:
    index = load_catalog_index(root)
    match = next((item for item in index.get("streams", []) if item.get("id") == stream_id), None)
    if not match:
        raise KeyError(f"stream id not found in catalog: {stream_id}")

    candidate_paths = []
    if match.get("path"):
        match_path = Path(match["path"])
        if match_path.is_absolute():
            candidate_paths.append(match_path)
        else:
            candidate_paths.append(repo_root() / match["path"])
            candidate_paths.append(root / "catalog-cache" / match["path"])
            candidate_paths.append(providers_root(root) / match["path"])
    candidate_paths.extend(provider_streams_root(root).glob("**/*.yaml"))
    candidate_paths.extend((repo_root() / "catalog" / "streams").glob("**/*.yaml"))

    for path in candidate_paths:
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("id") == stream_id:
            return data
    raise FileNotFoundError(f"stream definition not found for {stream_id}")


def schema_path_for_url(root: Path, schema_url: str) -> Path:
    name = schema_url.rstrip("/").split("/")[-1]
    for path in [provider_schemas_root(root) / name, builtin_event_schemas_root() / name]:
        if path.exists():
            return path
    raise FileNotFoundError(f"referenced schema not found locally: {schema_url}")


def validate_stream_file(path: Path, root: Path = DEFAULT_ROOT) -> None:
    stream = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = json.loads((repo_root() / "catalog" / "schemas" / "stream-definition.v0.3.json").read_text(encoding="utf-8"))
    jsonschema.validate(stream, schema)

    schema_path = schema_path_for_url(root, stream["schema_url"])
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


def validate_provider_tree(root: Path) -> list[Path]:
    stream_paths = sorted(provider_streams_root(root).glob("**/*.yaml"))
    seen: dict[str, Path] = {}
    builtin_ids = {stream["id"] for stream in json.loads((repo_root() / "catalog" / "INDEX.json").read_text(encoding="utf-8")).get("streams", [])}
    for path in stream_paths:
        validate_stream_file(path, root)
        stream_id = yaml.safe_load(path.read_text(encoding="utf-8"))["id"]
        if stream_id in builtin_ids:
            raise ValueError(f"{path}: local provider id conflicts with built-in provider: {stream_id}")
        if stream_id in seen:
            raise ValueError(f"{path}: duplicate local provider id also defined in {seen[stream_id]}: {stream_id}")
        seen[stream_id] = path
    return stream_paths


def substitute(value: object, parameters: dict) -> object:
    if isinstance(value, str):
        return PARAMETER_PATTERN.sub(
            lambda match: str(parameters[match.group(1)])
            if match.group(1) in parameters
            else match.group(0),
            value,
        )
    if isinstance(value, list):
        return [substitute(item, parameters) for item in value]
    if isinstance(value, dict):
        return {key: substitute(item, parameters) for key, item in value.items()}
    return value


def source_uri_for(stream: dict, parameters: dict) -> str:
    return substitute(stream["source_uri_template"], parameters)


def validate_parameters(stream: dict, parameters: dict) -> None:
    missing = [
        parameter["name"]
        for parameter in stream.get("parameters", [])
        if parameter.get("required") and parameter["name"] not in parameters
    ]
    if missing:
        raise ValueError(f"{stream['id']}: missing required parameters: {', '.join(missing)}")


def publisher_for(stream_uri: str) -> str:
    return urlparse(stream_uri).netloc


def stable_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def jmespath_search(expression: str | None, document: object) -> object:
    if not expression:
        return None
    return jmespath.search(expression, document)


def envelope(stream: dict, stream_uri: str, event_id: object, data: dict, event_time: str | None = None) -> dict:
    return {
        "specversion": AGENTFEEDS_VERSION,
        "id": str(event_id or stable_hash(data)),
        "source": stream_uri,
        "type": stream["type"],
        "time": event_time or now_utc(),
        "schema_url": stream["schema_url"],
        "schema_version": stream["schema_version"],
        "mode": stream["mode"],
        "data": data,
    }


def fetch_json(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    response = requests.request(
        adapter.get("method", "GET"),
        adapter["url"],
        headers=adapter.get("headers") or {},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    raw = response.json()
    expression = adapter.get("transform", {}).get("expression")
    transformed = jmespath_search(expression, raw) if expression else raw

    if adapter["kind"] == "json_http":
        if not isinstance(transformed, dict):
            raise ValueError(f"{stream['id']}: json_http transform must produce an object")
        event_id = jmespath_search(adapter.get("id_from"), raw) or stable_hash(transformed)
        return [envelope(stream, stream_uri, event_id, transformed)]

    if not isinstance(transformed, list):
        raise ValueError(f"{stream['id']}: paginated_json_http transform must produce an array")
    events = []
    for item in transformed:
        if not isinstance(item, dict):
            raise ValueError(f"{stream['id']}: paginated_json_http items must be objects")
        event_id = jmespath_search(adapter.get("id_from"), item) or stable_hash(item)
        events.append(envelope(stream, stream_uri, event_id, item))
    return events


def fetch_rss(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    parsed = feedparser.parse(adapter["url"])
    if parsed.bozo:
        raise ValueError(f"{stream['id']}: failed to parse RSS feed: {parsed.bozo_exception}")
    events = []
    for entry in parsed.entries:
        data = {
            "title": entry.get("title", ""),
            "link": entry.get("link"),
            "summary": entry.get("summary"),
            "published": entry.get("published"),
            "id": entry.get("id") or entry.get("guid") or entry.get("link"),
        }
        event_id = data["id"] or stable_hash(data)
        events.append(envelope(stream, stream_uri, event_id, data))
    return events


def serialize_ical_value(value: object) -> str | None:
    if value is None:
        return None
    decoded = getattr(value, "dt", value)
    if hasattr(decoded, "isoformat"):
        return decoded.isoformat()
    return str(decoded)


def fetch_ical(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    response = requests.get(adapter["url"], timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    calendar = icalendar.Calendar.from_ical(response.content)
    events = []
    for component in calendar.walk("VEVENT"):
        data = {
            "uid": str(component.get("uid", "")),
            "summary": str(component.get("summary", "")),
            "starts_at": serialize_ical_value(component.get("dtstart")),
            "ends_at": serialize_ical_value(component.get("dtend")),
            "location": str(component.get("location")) if component.get("location") else None,
        }
        events.append(envelope(stream, stream_uri, data["uid"] or stable_hash(data), data))
    return events


def fetch_local_file(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    path = Path(adapter["path"]).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"{stream['id']}: local file not found: {path}")
    if not path.is_file():
        raise ValueError(f"{stream['id']}: local path is not a file: {path}")

    raw = path.read_bytes()
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data = {
        "path": str(path),
        "name": path.name,
        "extension": path.suffix.lstrip("."),
        "content": raw.decode("utf-8", errors="replace"),
        "size_bytes": stat.st_size,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "modified_at": modified_at,
    }
    return [envelope(stream, stream_uri, data["sha256"], data, modified_at)]


def run_adapter(stream: dict, parameters: dict) -> tuple[str, list[dict]]:
    validate_parameters(stream, parameters)
    stream_uri = source_uri_for(stream, parameters)
    adapter = substitute(stream["adapter"], parameters)
    kind = adapter["kind"]
    if kind in {"json_http", "paginated_json_http"}:
        return stream_uri, fetch_json(stream, adapter, stream_uri)
    if kind == "rss":
        return stream_uri, fetch_rss(stream, adapter, stream_uri)
    if kind == "ical":
        return stream_uri, fetch_ical(stream, adapter, stream_uri)
    if kind == "local_file":
        return stream_uri, fetch_local_file(stream, adapter, stream_uri)
    raise ValueError(f"unsupported adapter kind: {kind}")


def value_at_path(payload: dict, dotted_path: str) -> object:
    current: object = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def comparison_matches(actual: object, expected: object) -> bool:
    if not isinstance(expected, dict):
        return actual == expected
    for operator, value in expected.items():
        if operator == "gte" and not (actual is not None and actual >= value):
            return False
        if operator == "gt" and not (actual is not None and actual > value):
            return False
        if operator == "lte" and not (actual is not None and actual <= value):
            return False
        if operator == "lt" and not (actual is not None and actual < value):
            return False
        if operator == "eq" and actual != value:
            return False
    return True


def event_matches_filter(event: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    for path, expected in filters.items():
        payload = event["data"] if path.startswith("data.") else event
        lookup = path.removeprefix("data.")
        if not comparison_matches(value_at_path(payload, lookup), expected):
            return False
    return True


def load_existing_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def poll_interval(subscription: dict, stream: dict, defaults: dict) -> int:
    return int(
        subscription.get("poll_interval_seconds")
        or defaults.get("poll_interval_seconds")
        or stream.get("recommended_poll_interval_seconds")
        or 600
    )


def provider_id_for(subscription: dict) -> str:
    return str(subscription["provider"])


def subscription_title(subscription: dict, stream: dict) -> str:
    return str(subscription.get("title") or stream.get("title") or subscription["id"])


def state_path_for_subscription(root: Path, subscription: dict) -> Path:
    stream = load_stream_definition(root, provider_id_for(subscription))
    stream_uri = source_uri_for(stream, subscription.get("parameters") or {})
    return state_path_for_stream(stream_uri, root)


def is_due(path: Path, interval_seconds: int, force: bool) -> bool:
    if force or not path.exists():
        return True
    existing = load_existing_state(path)
    if not existing:
        return True
    updated = parse_utc(existing.get("_meta", {}).get("last_updated"))
    if not updated:
        return True
    return datetime.now(UTC) - updated >= timedelta(seconds=interval_seconds)


def state_payload(
    subscription: dict,
    stream: dict,
    stream_uri: str,
    events: list[dict],
    existing: dict | None,
    interval_seconds: int,
    history_limit: int,
) -> dict:
    updated_at = now_utc()
    next_due = (
        datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=interval_seconds)
    ).isoformat().replace("+00:00", "Z")
    meta = {
        "stream": stream_uri,
        "type": stream["type"],
        "mode": stream["mode"],
        "last_updated": updated_at,
        "next_poll_due": next_due,
        "schema_url": stream["schema_url"],
        "schema_version": stream["schema_version"],
        "publisher": publisher_for(stream_uri),
        "stale": False,
        "subscription_id": subscription["id"],
        "provider_id": stream["id"],
        "title": subscription_title(subscription, stream),
    }

    if stream["mode"] == "snapshot":
        if not events:
            raise ValueError(f"{stream['id']}: snapshot adapter produced no events")
        return {"_meta": meta, "data": events[0]["data"]}

    if stream["mode"] == "event":
        old_events = existing.get("data", []) if existing else []
        merged = []
        seen = set()
        for event in [*events, *old_events]:
            event_id = event.get("id")
            if event_id in seen:
                continue
            seen.add(event_id)
            merged.append(event)
        return {"_meta": meta, "data": merged[:history_limit]}

    if stream["mode"] == "delta":
        current = existing.get("data", {}) if existing else {}
        for event in events:
            current.update(event["data"])
        return {"_meta": meta, "data": current}

    raise ValueError(f"unsupported mode: {stream['mode']}")


def regenerate_catalog(root: Path) -> None:
    lines = [
        "# Agent Feeds - Active Subscriptions",
        "",
        "This file lists data streams currently subscribed. Detailed state lives in `state/<...>.json`. Read those files when the user asks about the relevant topic.",
        "",
    ]
    state_entries = []
    try:
        subscriptions = load_subscriptions(root).get("subscriptions") or []
        for subscription in subscriptions:
            stream = load_stream_definition(root, provider_id_for(subscription))
            parameters = subscription.get("parameters") or {}
            stream_uri = source_uri_for(stream, parameters)
            path = state_path_for_stream(stream_uri, root)
            payload = load_existing_state(path) if path.exists() else {}
            meta = (payload or {}).get("_meta", {})
            state_entries.append((subscription, stream, stream_uri, path, meta))
    except Exception:
        state_entries = []
    if not state_entries:
        lines.extend(["No active state files found.", ""])

    for subscription, stream, stream_uri, path, meta in state_entries:
        title = subscription_title(subscription, stream)
        rel_path = path.relative_to(root)
        lines.extend(
            [
                f"## {title}",
                f"- **ID:** `{subscription.get('id', '')}`",
                f"- **Provider:** `{provider_id_for(subscription)}`",
                f"- **Stream:** `{meta.get('stream') or stream_uri}`",
                f"- **Path:** `{rel_path}`",
                f"- **Updated:** {meta.get('last_updated', 'never')}",
                f"- **Stale:** {'yes' if meta.get('stale') else 'no'}",
                f"- **Mode:** {meta.get('mode') or stream.get('mode', 'unknown')}",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            f"*Last regenerated: {now_utc()}. Agent: when the user asks about a topic above, read the corresponding state file. Do not web-search if a non-stale state file covers the question.*",
            "",
        ]
    )
    (root / "catalog.md").write_text("\n".join(lines), encoding="utf-8")


def run_fetch(args: argparse.Namespace, root: Path) -> int:
    subscriptions = load_subscriptions(root)
    defaults = subscriptions.get("defaults") or {}
    active = subscriptions.get("subscriptions") or []
    if args.once:
        active = [sub for sub in active if sub.get("id") == args.once]
    if args.stream:
        active = [sub for sub in active if sub.get("id") == args.stream]

    if not active:
        regenerate_catalog(root)
        return 0

    force = args.all or bool(args.stream) or bool(args.once)
    failures = 0
    for subscription in active:
        try:
            stream = load_stream_definition(root, provider_id_for(subscription))
            parameters = subscription.get("parameters") or {}
            stream_uri = source_uri_for(stream, parameters)
            path = state_path_for_stream(stream_uri, root)
            interval_seconds = poll_interval(subscription, stream, defaults)
            if not is_due(path, interval_seconds, force):
                continue

            stream_uri, events = run_adapter(stream, parameters)
            events = [event for event in events if event_matches_filter(event, subscription.get("filter"))]
            history_limit = int(subscription.get("history_limit") or defaults.get("history_limit") or 50)
            existing = load_existing_state(path)
            payload = state_payload(subscription, stream, stream_uri, events, existing, interval_seconds, history_limit)
            atomic_write_json(path, payload)
        except Exception as exc:  # noqa: BLE001 - keep cron-friendly failure reporting.
            failures += 1
            print(f"{subscription.get('id', '<unknown>')}: {exc}", file=sys.stderr)

    regenerate_catalog(root)
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Agent Feeds subscriptions")
    parser.add_argument("--all", action="store_true", help="refresh every subscription")
    parser.add_argument("--stream", help="refresh one subscription id")
    parser.add_argument("--once", help="one-shot fetch for a subscription id")
    parser.add_argument("--regenerate-catalog", action="store_true", help="regenerate catalog.md without polling")
    parser.add_argument("--update-catalog", action="store_true", help="refresh the local catalog cache")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="agentfeeds root directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser()
    ensure_root(root)

    if args.update_catalog:
        update_catalog_cache(root)
    if args.regenerate_catalog:
        regenerate_catalog(root)
        return 0
    return run_fetch(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
