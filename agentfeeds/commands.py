"""User-facing Agent Feeds management CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
import yaml

from agentfeeds import fetcher as fetch
from agentfeeds.constants import REQUEST_TIMEOUT_SECONDS


INSTANCE_ID_PATTERN = re.compile(r"^[a-z0-9-]+/[a-z0-9][a-z0-9-]*$")
ADAPTER_KINDS = {
    "local_file": "Read one local text, Markdown, or JSON file as a snapshot.",
    "local_command": "Run an argv-only local command for a snapshot or JSON-derived events.",
    "json_http": "Fetch one HTTP JSON document and transform it into a snapshot.",
    "paginated_json_http": "Fetch an HTTP JSON array and transform it into event items.",
    "rss": "Fetch an RSS or Atom feed as event items.",
    "ical": "Fetch an iCalendar URL as event items.",
}


def parse_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_params(items: list[str]) -> dict[str, Any]:
    params = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"parameters must be key=value, got: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise SystemExit(f"parameter key cannot be empty: {item}")
        params[key] = parse_value(value)
    return params


def save_subscriptions(root: Path, config: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "subscriptions.yaml"
    tmp_path = path.with_suffix(".yaml.tmp")
    tmp_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    tmp_path.replace(path)


def active_subscriptions(root: Path) -> dict:
    fetch.ensure_root(root)
    return fetch.load_subscriptions(root)


def stream_summary(root: Path, stream_id: str) -> dict:
    return fetch.load_stream_definition(root, stream_id)


def template_id_for(subscription: dict) -> str:
    return str(subscription["template"])


def state_path_for_subscription(root: Path, subscription: dict) -> Path | None:
    try:
        stream = fetch.load_stream_definition(root, template_id_for(subscription))
        stream_uri = fetch.source_uri_for(stream, subscription.get("parameters") or {})
        return fetch.state_path_for_stream(stream_uri, root)
    except Exception:
        return None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "feed"


def _hash_suffix(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:6]


def _template_id_parts(template_id: str) -> tuple[str, str]:
    if not INSTANCE_ID_PATTERN.match(template_id):
        raise ValueError("template id must look like category/name using lowercase letters, numbers, and hyphens")
    return tuple(template_id.split("/", 1))  # type: ignore[return-value]


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def _schema_payload(template_id: str, mode: str) -> dict:
    category, name = _template_id_parts(template_id)
    type_name = f"{category}.{name.replace('-', '.')}"
    data = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://agentfeeds.dev/schemas/{type_name}.v1.json",
        "title": _title_from_slug(name),
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "url": {"type": ["string", "null"]},
            "content": {"type": ["string", "null"]},
            "updated_at": {"type": ["string", "null"]},
            "stdout": {"type": ["string", "null"]},
            "transformed": {},
        },
    }
    if mode == "event":
        data["required"] = ["title"]
    return data


def scaffold_stream(template_id: str, adapter_kind: str) -> tuple[dict, dict, Path, Path]:
    if adapter_kind not in ADAPTER_KINDS:
        raise ValueError(f"unsupported adapter kind: {adapter_kind}")
    category, name = _template_id_parts(template_id)
    title = _title_from_slug(name)
    type_name = f"{category}.{name.replace('-', '.')}"
    mode = "event" if adapter_kind in {"paginated_json_http", "rss", "ical"} else "snapshot"
    schema_name = f"{type_name}.v1.json"
    stream_path = Path(category) / f"{name}.yaml"
    schema_path = Path(schema_name)

    parameters = []
    source_uri_template = f"feed://{type_name}/source"
    adapter: dict[str, object] = {"kind": adapter_kind}
    transform = {
        "language": "jmespath",
        "expression": "{title: title, url: url, content: body, updated_at: updated_at}",
    }

    if adapter_kind == "local_file":
        parameters = [{"name": "path", "type": "string", "description": "Local file path", "required": True}]
        source_uri_template = f"feed://{type_name}/file?path={{path}}"
        adapter = {"kind": "local_file", "path": "{path}"}
    elif adapter_kind == "local_command":
        parameters = []
        source_uri_template = f"feed://{type_name}/command"
        adapter = {
            "kind": "local_command",
            "command": ["echo", "{\"title\":\"example\",\"status\":\"ok\"}"],
            "timeout_seconds": 20,
            "max_output_bytes": 1048576,
            "parse": "json",
            "transform": {
                "language": "jmespath",
                "expression": "{title: title, content: status}",
            },
        }
        type_name = "local.command"
        schema_name = "local.command.v1.json"
        schema_path = Path(schema_name)
    elif adapter_kind == "json_http":
        parameters = [{"name": "url", "type": "string", "description": "JSON API URL", "required": True}]
        source_uri_template = f"feed://{type_name}/json?url={{url}}"
        adapter = {"kind": "json_http", "url": "{url}", "method": "GET", "headers": {}, "transform": transform}
    elif adapter_kind == "paginated_json_http":
        parameters = [{"name": "url", "type": "string", "description": "JSON API URL", "required": True}]
        source_uri_template = f"feed://{type_name}/items?url={{url}}"
        adapter = {"kind": "paginated_json_http", "url": "{url}", "method": "GET", "headers": {}, "transform": transform, "id_from": "url"}
    elif adapter_kind == "rss":
        parameters = [{"name": "url", "type": "string", "description": "RSS or Atom URL", "required": True}]
        source_uri_template = f"feed://{type_name}/rss?url={{url}}"
        adapter = {"kind": "rss", "url": "{url}"}
        type_name = "rss.item"
        schema_name = "rss-item.v1.json"
        schema_path = Path(schema_name)
    elif adapter_kind == "ical":
        parameters = [{"name": "url", "type": "string", "description": "iCalendar URL", "required": True}]
        source_uri_template = f"feed://{type_name}/ics?url={{url}}"
        adapter = {"kind": "ical", "url": "{url}"}
        type_name = "ical.event"
        schema_name = "ical-event.v1.json"
        schema_path = Path(schema_name)

    stream = {
        "id": template_id,
        "title": title,
        "description": f"Draft template for {title}.",
        "type": type_name,
        "mode": mode,
        "schema_url": f"https://agentfeeds.dev/schemas/{schema_name}",
        "schema_version": "1.0.0",
        "parameters": parameters,
        "source_uri_template": source_uri_template,
        "adapter": adapter,
        "recommended_poll_interval_seconds": 300,
        "auth": "none",
        "tags": [category, adapter_kind.replace("_", "-")],
        "quality_tier": "experimental",
        "contributed_by": "local",
    }
    return stream, _schema_payload(template_id, mode), stream_path, schema_path


def _domain_slug(domain: str) -> str:
    return _slugify(domain.removeprefix("www.").rstrip(".").replace(".", "-"))


def _domain_title(domain: str, suffix: str = "RSS feed") -> str:
    base = domain.removeprefix("www.").split(".")[0]
    return f"{base.replace('-', ' ').title()} {suffix}".strip()


def _rss_identity(url: str) -> tuple[str | None, str | None]:
    parsed = None
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except Exception:
        parsed = None

    domains = []
    if parsed is not None:
        for entry in getattr(parsed, "entries", []) or []:
            link = entry.get("link")
            if not link:
                continue
            domain = urlparse(link).netloc.lower()
            if domain:
                domains.append(domain)

    domain = None
    if domains:
        domain = Counter(domains).most_common(1)[0][0]
    if not domain:
        domain = urlparse(url).netloc.lower() or None

    title = None
    if parsed is not None:
        feed = getattr(parsed, "feed", {}) or {}
        if feed.get("title"):
            title = str(feed["title"])
    if not title and domain:
        title = _domain_title(domain)
    return domain, title


def _default_identity(template: dict, params: dict[str, Any]) -> tuple[str, str]:
    template_id = template["id"]
    parameters = template.get("parameters") or []
    if not parameters:
        return template_id, template["title"]

    category = template_id.split("/", 1)[0]
    title = template["title"]

    if template_id == "local/file" and params.get("path"):
        path = Path(str(params["path"])).expanduser()
        name = path.name or "file"
        return f"{category}/{_slugify(name)}", name

    if params.get("owner") and params.get("repo"):
        owner = _slugify(str(params["owner"]))
        repo = _slugify(str(params["repo"]))
        suffixes = {
            "dev/github-issues": "issues",
            "dev/github-prs": "prs",
            "dev/github-releases": "releases",
        }
        suffix = suffixes.get(template_id, template_id.split("/", 1)[1])
        return f"{category}/{owner}-{repo}-{suffix}", f"{params['owner']}/{params['repo']} {suffix}"

    if template_id == "calendar/ics" and params.get("url"):
        parsed = urlparse(str(params["url"]))
        if parsed.netloc:
            return f"{category}/{_domain_slug(parsed.netloc)}", f"{_domain_title(parsed.netloc, 'calendar')}"

    if template_id == "news/rss-generic" and params.get("url"):
        domain, rss_title = _rss_identity(str(params["url"]))
        if domain:
            return f"{category}/{_domain_slug(domain)}", rss_title or _domain_title(domain)

    if params.get("url"):
        parsed = urlparse(str(params["url"]))
        if parsed.netloc:
            return f"{category}/{_domain_slug(parsed.netloc)}", _domain_title(parsed.netloc)

    if params.get("base"):
        base = str(params["base"]).upper()
        return f"{category}/{_slugify(base)}-exchange-rates", f"{base} exchange rates"

    if params.get("lat") is not None and params.get("lon") is not None:
        lat = _slugify(str(params["lat"]))
        lon = _slugify(str(params["lon"]))
        tail = _slugify(template_id.split("/", 1)[1])
        return f"{category}/{tail}-{lat}-{lon}", title

    return f"{category}/{_slugify(template_id)}-{_hash_suffix(params)}", title


def _append_collision_suffix(instance_id: str, template: dict, params: dict[str, Any], existing_ids: set[str]) -> str:
    if instance_id not in existing_ids:
        return instance_id

    path = ""
    if params.get("url"):
        parsed_path = urlparse(str(params["url"])).path.strip("/")
        if parsed_path:
            path = _slugify(parsed_path.split("/")[-2] if parsed_path.endswith("/") else parsed_path.rsplit("/", 1)[-1])
    if path:
        candidate = f"{instance_id}-{path}"
        if candidate not in existing_ids:
            return candidate

    return f"{instance_id}-{_hash_suffix({'template': template['id'], 'parameters': params})}"


def materialize_subscription(
    template: dict,
    params: dict[str, Any],
    existing_ids: set[str],
    instance_id: str | None = None,
    title: str | None = None,
) -> dict:
    default_id, default_title = _default_identity(template, params)
    if instance_id:
        resolved_id = instance_id
    elif not template.get("parameters"):
        resolved_id = default_id
    else:
        resolved_id = _append_collision_suffix(default_id, template, params, existing_ids)
    resolved_title = title or default_title
    if not INSTANCE_ID_PATTERN.match(resolved_id):
        raise ValueError(
            "subscription id must look like category/name using lowercase letters, numbers, and hyphens"
        )
    if resolved_id in existing_ids:
        raise ValueError(f"subscription id already exists: {resolved_id}")

    subscription = {
        "id": resolved_id,
        "title": resolved_title,
        "template": template["id"],
    }
    if params:
        subscription["parameters"] = params
    return subscription


def cmd_templates_search(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    index = fetch.load_catalog_index(args.root)
    query = " ".join(args.query).lower().strip()
    streams = index.get("streams") or []
    if query:
        streams = [
            stream
            for stream in streams
            if query
            in " ".join(
                [
                    stream.get("id", ""),
                    stream.get("title", ""),
                    stream.get("description", ""),
                    " ".join(stream.get("tags") or []),
                    stream.get("type", ""),
                ]
            ).lower()
        ]
    for stream in streams:
        params = ", ".join(stream.get("parameters") or []) or "none"
        source = f", source: {stream.get('source')}" if args.verbose and stream.get("source") else ""
        print(f"{stream['id']}: {stream['title']} [params: {params}, mode: {stream['mode']}{source}]")
        if args.verbose:
            print(f"  {stream.get('description', '')}")
    return 0


def cmd_templates_show(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    try:
        stream = fetch.load_stream_definition(args.root, args.template_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = {
        "id": stream["id"],
        "title": stream["title"],
        "description": stream["description"],
        "type": stream["type"],
        "mode": stream["mode"],
        "parameters": stream.get("parameters") or [],
        "auth": stream.get("auth"),
        "quality_tier": stream.get("quality_tier"),
        "tags": stream.get("tags") or [],
        "recommended_poll_interval_seconds": stream.get("recommended_poll_interval_seconds"),
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    required = [
        parameter["name"]
        for parameter in result["parameters"]
        if parameter.get("required")
    ]
    optional = [
        parameter["name"]
        for parameter in result["parameters"]
        if not parameter.get("required")
    ]
    print(f"{result['id']}: {result['title']}")
    print(result["description"])
    print(f"Type: {result['type']}")
    print(f"Mode: {result['mode']}")
    print(f"Required parameters: {', '.join(required) or 'none'}")
    print(f"Optional parameters: {', '.join(optional) or 'none'}")
    print(f"Auth: {result['auth']}")
    print(f"Quality: {result['quality_tier']}")
    return 0


def cmd_subscribe(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    config.setdefault("version", fetch.SPEC_VERSION)
    config.setdefault("defaults", {"poll_interval_seconds": 600, "history_limit": 50})
    subscriptions = config.setdefault("subscriptions", [])

    try:
        stream = fetch.load_stream_definition(args.root, args.template_id)
        params = parse_params(args.parameters)
        fetch.validate_parameters(stream, params)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    existing_ids = {str(item.get("id")) for item in subscriptions}
    try:
        subscription = materialize_subscription(stream, params, existing_ids, args.instance_id, args.title)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.poll_interval_seconds:
        subscription["poll_interval_seconds"] = args.poll_interval_seconds
    if args.history_limit:
        subscription["history_limit"] = args.history_limit

    subscriptions.append(subscription)
    save_subscriptions(args.root, config)
    print(f"Subscribed: {subscription['id']} ({subscription['title']})")

    if args.no_fetch:
        fetch.regenerate_catalog(args.root)
        return 0
    return fetch.main(["--root", str(args.root), "--once", subscription["id"]])


def cmd_unsubscribe(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    subscriptions = config.get("subscriptions") or []
    matches = [
        subscription
        for subscription in subscriptions
        if subscription.get("id") == args.subscription_id
    ]
    if not matches:
        print(f"No matching subscription: {args.subscription_id}", file=sys.stderr)
        return 1

    remove_keys = {id(match) for match in matches}
    state_paths = [state_path_for_subscription(args.root, match) for match in matches]
    config["subscriptions"] = [
        subscription for subscription in subscriptions if id(subscription) not in remove_keys
    ]
    save_subscriptions(args.root, config)

    if not args.keep_state:
        for path in state_paths:
            if path and path.exists() and args.root in path.parents:
                path.unlink()

    fetch.regenerate_catalog(args.root)
    print(f"Unsubscribed: {args.subscription_id}")
    return 0


def state_status(root: Path, subscription: dict, defaults: dict) -> dict:
    stream = stream_summary(root, template_id_for(subscription))
    path = state_path_for_subscription(root, subscription)
    interval = fetch.poll_interval(subscription, stream, defaults)
    payload = fetch.load_existing_state(path) if path else None
    meta = (payload or {}).get("_meta", {})
    updated = fetch.parse_utc(meta.get("last_updated"))
    stale = True
    due = True
    if updated:
        age = datetime.now(UTC) - updated
        due = age >= timedelta(seconds=interval)
        stale = age > timedelta(seconds=interval * 2)
    return {
        "id": subscription["id"],
        "title": subscription.get("title") or stream.get("title"),
        "template": subscription.get("template"),
        "parameters": subscription.get("parameters") or {},
        "path": str(path.relative_to(root)) if path else "",
        "exists": bool(path and path.exists()),
        "last_updated": meta.get("last_updated"),
        "next_poll_due": meta.get("next_poll_due"),
        "due": due,
        "stale": stale,
        "mode": stream.get("mode"),
    }


def _stream_rows(root: Path) -> list[dict]:
    config = active_subscriptions(root)
    defaults = config.get("defaults") or {}
    return [state_status(root, subscription, defaults) for subscription in config.get("subscriptions") or []]


def _stream_matches(row: dict, query: str) -> bool:
    haystack = " ".join(
        [
            row.get("id", ""),
            row.get("title", ""),
            row.get("template", ""),
            " ".join(f"{key}={value}" for key, value in sorted((row.get("parameters") or {}).items())),
            row.get("mode", ""),
        ]
    ).lower()
    return query.lower() in haystack


def _print_stream_rows(rows: list[dict]) -> None:
    if not rows:
        print("No active streams.")
        return
    for row in rows:
        freshness = "stale" if row["stale"] else "due" if row["due"] else "fresh"
        exists = "ok" if row["exists"] else "missing"
        print(f"{row['id']}: {row['title']} [{freshness}, {exists}, updated={row['last_updated'] or 'never'}]")


def cmd_streams_list(args: argparse.Namespace) -> int:
    rows = _stream_rows(args.root)
    if args.json:
        print(json.dumps({"streams": rows}, indent=2, sort_keys=True))
        return 0
    _print_stream_rows(rows)
    return 0


def cmd_streams_search(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    rows = _stream_rows(args.root)
    if query:
        rows = [row for row in rows if _stream_matches(row, query)]
    if args.json:
        print(json.dumps({"streams": rows}, indent=2, sort_keys=True))
        return 0
    _print_stream_rows(rows)
    return 0


def _subscription_by_id(root: Path, subscription_id: str) -> tuple[dict, dict]:
    config = active_subscriptions(root)
    for subscription in config.get("subscriptions") or []:
        if subscription.get("id") == subscription_id:
            return config, subscription
    raise KeyError(f"No matching subscription: {subscription_id}")


def _stream_detail(root: Path, subscription_id: str) -> dict:
    config, subscription = _subscription_by_id(root, subscription_id)
    defaults = config.get("defaults") or {}
    row = state_status(root, subscription, defaults)
    stream = fetch.load_stream_definition(root, template_id_for(subscription))
    parameters = subscription.get("parameters") or {}
    stream_uri = fetch.source_uri_for(stream, parameters)
    path = fetch.state_path_for_stream(stream_uri, root)
    payload = fetch.load_existing_state(path) if path.exists() else None
    meta = (payload or {}).get("_meta", {})
    data = (payload or {}).get("data")
    data_summary = {"kind": type(data).__name__}
    if isinstance(data, list):
        data_summary["count"] = len(data)
    elif isinstance(data, dict):
        data_summary["keys"] = sorted(data.keys())
    return {
        **row,
        "template": row.get("template"),
        "stream": stream_uri,
        "state_path": str(path.relative_to(root)),
        "meta": meta,
        "data_summary": data_summary,
    }


def cmd_streams_show(args: argparse.Namespace) -> int:
    try:
        result = _stream_detail(args.root, args.subscription_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print(f"{result['id']}: {result['title']}")
    print(f"Template: {result['template']}")
    print(f"Mode: {result['mode']}")
    print(f"Freshness: {'stale' if result['stale'] else 'due' if result['due'] else 'fresh'}")
    print(f"Updated: {result['last_updated'] or 'never'}")
    print(f"State path: {result['state_path']}")
    print(f"Stream: {result['stream']}")
    print(f"Data: {json.dumps(result['data_summary'], sort_keys=True)}")
    return 0


def _limited_data(data: object, limit: int | None) -> object:
    if limit is None:
        return data
    if isinstance(data, list):
        return data[:limit]
    return data


def cmd_streams_read(args: argparse.Namespace) -> int:
    try:
        detail = _stream_detail(args.root, args.subscription_id)
        path = args.root / detail["state_path"]
        payload = fetch.load_existing_state(path)
        if payload is None:
            raise FileNotFoundError(f"state file not found or invalid: {detail['state_path']}")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    data = _limited_data(payload.get("data"), args.limit)
    result = {
        "id": detail["id"],
        "title": detail["title"],
        "template": detail["template"],
        "state_path": detail["state_path"],
        "stale": detail["stale"],
        "last_updated": detail["last_updated"],
        "data": data,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(f"{result['id']}: {result['title']}")
    print(f"Template: {result['template']}")
    print(f"State path: {result['state_path']}")
    print(f"Updated: {result['last_updated'] or 'never'}")
    print(f"Stale: {'yes' if result['stale'] else 'no'}")
    print("Data:")
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.all:
        return fetch.main(["--root", str(args.root), "--all"])
    if not args.subscription_id:
        print("refresh requires a subscription id or --all", file=sys.stderr)
        return 2
    return fetch.main(["--root", str(args.root), "--stream", args.subscription_id])


def cmd_templates_list(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    index = fetch.load_catalog_index(args.root)
    for stream in index.get("streams") or []:
        params = ", ".join(stream.get("parameters") or []) or "none"
        print(f"{stream['id']}: {stream['title']} [params: {params}, source: {stream.get('source', 'builtin')}]")
    return 0


def cmd_templates_path(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    print(fetch.templates_root(args.root))
    return 0


def cmd_templates_validate(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    try:
        paths = fetch.validate_template_tree(args.root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not paths:
        print(f"No local templates found in {fetch.template_streams_root(args.root)}")
        return 0
    for path in paths:
        print(f"valid: {path}")
    return 0


def cmd_templates_adapters(_args: argparse.Namespace) -> int:
    for kind, description in ADAPTER_KINDS.items():
        print(f"{kind}: {description}")
    return 0


def cmd_templates_scaffold(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    try:
        stream, schema, stream_rel_path, schema_rel_path = scaffold_stream(args.template_id, args.adapter_kind)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    stream_path = fetch.template_streams_root(args.root) / stream_rel_path
    schema_path = fetch.template_schemas_root(args.root) / schema_rel_path
    if stream_path.exists() and not args.force:
        print(f"template already exists: {stream_path}", file=sys.stderr)
        return 1

    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(yaml.safe_dump(stream, sort_keys=False), encoding="utf-8")

    if args.adapter_kind not in {"rss", "ical", "local_command"} and (args.force or not schema_path.exists()):
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote: {stream_path}")
    if args.adapter_kind in {"rss", "ical", "local_command"}:
        print(f"schema: built-in {stream['schema_url']}")
    else:
        print(f"wrote: {schema_path}")
    print("Next: edit the draft, then run `agentfeeds templates validate`.")
    return 0


def _event_sample(events: list[dict]) -> object:
    if not events:
        return None
    return events[0].get("data")


def cmd_templates_test(args: argparse.Namespace) -> int:
    fetch.ensure_root(args.root)
    try:
        stream = fetch.load_stream_definition(args.root, args.template_id)
        params = parse_params(args.parameters)
        fetch.validate_parameters(stream, params)
        stream_uri, events = fetch.run_adapter(stream, params)
        state_path = fetch.state_path_for_stream(stream_uri, args.root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = {
        "template": stream["id"],
        "title": stream["title"],
        "mode": stream["mode"],
        "stream": stream_uri,
        "state_path": str(state_path.relative_to(args.root)),
        "event_count": len(events),
        "sample": _event_sample(events),
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(f"Template: {result['template']}")
    print(f"Title: {result['title']}")
    print(f"Mode: {result['mode']}")
    print(f"Stream: {result['stream']}")
    print(f"State path: {result['state_path']}")
    print(f"Events: {result['event_count']}")
    print("Sample:")
    print(json.dumps(result["sample"], indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Agent Feeds subscriptions")
    parser.add_argument("--root", type=Path, default=fetch.DEFAULT_ROOT, help="agentfeeds root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subscribe = subparsers.add_parser("subscribe", help="add a subscription")
    subscribe.add_argument("template_id")
    subscribe.add_argument("parameters", nargs="*", help="template parameters as key=value")
    subscribe.add_argument("--id", dest="instance_id", help="concrete subscription id to create")
    subscribe.add_argument("--title", help="concrete subscription title")
    subscribe.add_argument("--poll-interval-seconds", type=int)
    subscribe.add_argument("--history-limit", type=int)
    subscribe.add_argument("--no-fetch", action="store_true")
    subscribe.set_defaults(func=cmd_subscribe)

    unsubscribe = subparsers.add_parser("unsubscribe", help="remove a subscription")
    unsubscribe.add_argument("subscription_id")
    unsubscribe.add_argument("--keep-state", action="store_true")
    unsubscribe.set_defaults(func=cmd_unsubscribe)

    refresh = subparsers.add_parser("refresh", help="refresh subscriptions")
    refresh.add_argument("subscription_id", nargs="?")
    refresh.add_argument("--all", action="store_true")
    refresh.set_defaults(func=cmd_refresh)

    streams = subparsers.add_parser("streams", help="inspect and read active streams")
    stream_subparsers = streams.add_subparsers(dest="stream_command", required=True)
    streams_list = stream_subparsers.add_parser("list", help="list active streams")
    streams_list.add_argument("--json", action="store_true")
    streams_list.set_defaults(func=cmd_streams_list)
    streams_search = stream_subparsers.add_parser("search", help="search active streams")
    streams_search.add_argument("query", nargs="*")
    streams_search.add_argument("--json", action="store_true")
    streams_search.set_defaults(func=cmd_streams_search)
    streams_show = stream_subparsers.add_parser("show", help="show active stream metadata")
    streams_show.add_argument("subscription_id")
    streams_show.add_argument("--json", action="store_true")
    streams_show.set_defaults(func=cmd_streams_show)
    streams_read = stream_subparsers.add_parser("read", help="read active stream data")
    streams_read.add_argument("subscription_id")
    streams_read.add_argument("--limit", type=int, default=20, help="limit event-list data rows")
    streams_read.add_argument("--json", action="store_true", help="print machine-readable output")
    streams_read.set_defaults(func=cmd_streams_read)

    templates = subparsers.add_parser("templates", help="browse and test feed templates")
    template_subparsers = templates.add_subparsers(dest="template_command", required=True)
    template_search = template_subparsers.add_parser("search", help="search built-in and local templates")
    template_search.add_argument("query", nargs="*")
    template_search.add_argument("-v", "--verbose", action="store_true")
    template_search.set_defaults(func=cmd_templates_search)
    template_subparsers.add_parser("list", help="list built-in and local templates").set_defaults(func=cmd_templates_list)
    template_show = template_subparsers.add_parser("show", help="show one template")
    template_show.add_argument("template_id")
    template_show.add_argument("--json", action="store_true")
    template_show.set_defaults(func=cmd_templates_show)
    template_subparsers.add_parser("adapters", help="list scaffoldable adapter kinds").set_defaults(func=cmd_templates_adapters)
    template_subparsers.add_parser("path", help="print the local template directory").set_defaults(func=cmd_templates_path)
    scaffold = template_subparsers.add_parser("scaffold", help="create a draft local template")
    scaffold.add_argument("adapter_kind", choices=sorted(ADAPTER_KINDS))
    scaffold.add_argument("template_id", metavar="template_id")
    scaffold.add_argument("--force", action="store_true", help="overwrite an existing draft")
    scaffold.set_defaults(func=cmd_templates_scaffold)
    template_test = template_subparsers.add_parser("test", help="run a template once without writing state")
    template_test.add_argument("template_id", metavar="template_id")
    template_test.add_argument("parameters", nargs="*", help="template parameters as key=value")
    template_test.add_argument("--json", action="store_true", help="print machine-readable output")
    template_test.set_defaults(func=cmd_templates_test)
    template_subparsers.add_parser("validate", help="validate local templates").set_defaults(func=cmd_templates_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.root = args.root.expanduser()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
