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

import yaml

from agentfeeds import fetch


INSTANCE_ID_PATTERN = re.compile(r"^[a-z0-9-]+/[a-z0-9][a-z0-9-]*$")


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


def provider_id_for(subscription: dict) -> str:
    return str(subscription["provider"])


def state_path_for_subscription(root: Path, subscription: dict) -> Path | None:
    try:
        stream = fetch.load_stream_definition(root, provider_id_for(subscription))
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


def _domain_slug(domain: str) -> str:
    return _slugify(domain.removeprefix("www.").rstrip(".").replace(".", "-"))


def _domain_title(domain: str, suffix: str = "RSS feed") -> str:
    base = domain.removeprefix("www.").split(".")[0]
    return f"{base.replace('-', ' ').title()} {suffix}".strip()


def _rss_identity(url: str) -> tuple[str | None, str | None]:
    parsed = None
    try:
        response = fetch.requests.get(url, timeout=fetch.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        parsed = fetch.feedparser.parse(response.content)
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


def _default_identity(provider: dict, params: dict[str, Any]) -> tuple[str, str]:
    provider_id = provider["id"]
    parameters = provider.get("parameters") or []
    if not parameters:
        return provider_id, provider["title"]

    category = provider_id.split("/", 1)[0]
    title = provider["title"]

    if provider_id == "local/file" and params.get("path"):
        path = Path(str(params["path"])).expanduser()
        name = path.name or "file"
        return f"{category}/{_slugify(name)}", name

    if provider_id == "news/rss-generic" and params.get("url"):
        domain, rss_title = _rss_identity(str(params["url"]))
        if domain:
            return f"{category}/{_domain_slug(domain)}", rss_title or _domain_title(domain)

    if params.get("url"):
        parsed = urlparse(str(params["url"]))
        if parsed.netloc:
            return f"{category}/{_domain_slug(parsed.netloc)}", _domain_title(parsed.netloc)

    if params.get("owner") and params.get("repo"):
        owner = _slugify(str(params["owner"]))
        repo = _slugify(str(params["repo"]))
        return f"{category}/{owner}-{repo}-releases", f"{params['owner']}/{params['repo']} releases"

    if params.get("base"):
        base = str(params["base"]).upper()
        return f"{category}/{_slugify(base)}-exchange-rates", f"{base} exchange rates"

    if params.get("lat") is not None and params.get("lon") is not None:
        lat = _slugify(str(params["lat"]))
        lon = _slugify(str(params["lon"]))
        tail = _slugify(provider_id.split("/", 1)[1])
        return f"{category}/{tail}-{lat}-{lon}", title

    return f"{category}/{_slugify(provider_id)}-{_hash_suffix(params)}", title


def _append_collision_suffix(instance_id: str, provider: dict, params: dict[str, Any], existing_ids: set[str]) -> str:
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

    return f"{instance_id}-{_hash_suffix({'provider': provider['id'], 'parameters': params})}"


def materialize_subscription(
    provider: dict,
    params: dict[str, Any],
    existing_ids: set[str],
    instance_id: str | None = None,
    title: str | None = None,
) -> dict:
    default_id, default_title = _default_identity(provider, params)
    if instance_id:
        resolved_id = instance_id
    elif not provider.get("parameters"):
        resolved_id = default_id
    else:
        resolved_id = _append_collision_suffix(default_id, provider, params, existing_ids)
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
        "provider": provider["id"],
    }
    if params:
        subscription["parameters"] = params
    return subscription


def cmd_list(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    subscriptions = config.get("subscriptions") or []
    if not subscriptions:
        print("No active subscriptions.")
        return 0
    for index, subscription in enumerate(subscriptions, start=1):
        params = subscription.get("parameters") or {}
        suffix = " ".join(f"{key}={value}" for key, value in sorted(params.items()))
        title = subscription.get("title") or subscription["id"]
        provider = subscription.get("provider")
        provider_suffix = f" ({provider})" if provider and provider != subscription["id"] else ""
        print(f"{index}. {subscription['id']}: {title}{provider_suffix}" + (f" {suffix}" if suffix else ""))
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
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
        print(f"{stream['id']}: {stream['title']} [params: {params}, mode: {stream['mode']}]")
        if args.verbose:
            print(f"  {stream.get('description', '')}")
    return 0


def cmd_subscribe(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    config.setdefault("version", fetch.SPEC_VERSION)
    config.setdefault("defaults", {"poll_interval_seconds": 600, "history_limit": 50})
    subscriptions = config.setdefault("subscriptions", [])

    try:
        stream = fetch.load_stream_definition(args.root, args.provider_id)
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
    stream = stream_summary(root, provider_id_for(subscription))
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
        "provider": subscription.get("provider"),
        "parameters": subscription.get("parameters") or {},
        "path": str(path.relative_to(root)) if path else "",
        "exists": bool(path and path.exists()),
        "last_updated": meta.get("last_updated"),
        "next_poll_due": meta.get("next_poll_due"),
        "due": due,
        "stale": stale,
        "mode": stream.get("mode"),
    }


def cmd_status(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    defaults = config.get("defaults") or {}
    rows = [state_status(args.root, subscription, defaults) for subscription in config.get("subscriptions") or []]
    if args.json:
        print(json.dumps({"subscriptions": rows}, indent=2, sort_keys=True))
        return 0
    if not rows:
        print("No active subscriptions.")
        return 0
    for row in rows:
        freshness = "stale" if row["stale"] else "due" if row["due"] else "fresh"
        exists = "ok" if row["exists"] else "missing"
        params = " ".join(f"{key}={value}" for key, value in sorted(row["parameters"].items()))
        label = row["id"] + (f" {params}" if params else "")
        print(f"{label}: {row['title']}, {freshness}, {exists}, updated={row['last_updated'] or 'never'}")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.all:
        return fetch.main(["--root", str(args.root), "--all"])
    if not args.subscription_id:
        print("refresh requires a subscription id or --all", file=sys.stderr)
        return 2
    return fetch.main(["--root", str(args.root), "--stream", args.subscription_id])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Agent Feeds subscriptions")
    parser.add_argument("--root", type=Path, default=fetch.DEFAULT_ROOT, help="agentfeeds root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="list active subscriptions").set_defaults(func=cmd_list)

    discover = subparsers.add_parser("discover", help="discover catalog streams")
    discover.add_argument("query", nargs="*")
    discover.add_argument("-v", "--verbose", action="store_true")
    discover.set_defaults(func=cmd_discover)

    subscribe = subparsers.add_parser("subscribe", help="add a subscription")
    subscribe.add_argument("provider_id")
    subscribe.add_argument("parameters", nargs="*", help="stream parameters as key=value")
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

    status = subparsers.add_parser("status", help="show subscription state status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.root = args.root.expanduser()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
