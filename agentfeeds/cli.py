"""User-facing Agent Feeds management CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from agentfeeds import fetch


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


def subscription_key(subscription: dict) -> tuple[str, tuple[tuple[str, str], ...]]:
    params = subscription.get("parameters") or {}
    return (
        str(subscription.get("id", "")),
        tuple(sorted((str(key), str(value)) for key, value in params.items())),
    )


def stream_summary(root: Path, stream_id: str) -> dict:
    return fetch.load_stream_definition(root, stream_id)


def state_path_for_subscription(root: Path, subscription: dict) -> Path | None:
    try:
        stream = fetch.load_stream_definition(root, subscription["id"])
        stream_uri = fetch.source_uri_for(stream, subscription.get("parameters") or {})
        return fetch.state_path_for_stream(stream_uri, root)
    except Exception:
        return None


def cmd_list(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    subscriptions = config.get("subscriptions") or []
    if not subscriptions:
        print("No active subscriptions.")
        return 0
    for index, subscription in enumerate(subscriptions, start=1):
        params = subscription.get("parameters") or {}
        suffix = " ".join(f"{key}={value}" for key, value in sorted(params.items()))
        print(f"{index}. {subscription['id']}" + (f" {suffix}" if suffix else ""))
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

    stream = fetch.load_stream_definition(args.root, args.stream_id)
    params = parse_params(args.parameters)
    fetch.validate_parameters(stream, params)

    subscription = {"id": args.stream_id}
    if params:
        subscription["parameters"] = params
    if args.poll_interval_seconds:
        subscription["poll_interval_seconds"] = args.poll_interval_seconds
    if args.history_limit:
        subscription["history_limit"] = args.history_limit

    existing_keys = {subscription_key(item) for item in subscriptions}
    if subscription_key(subscription) in existing_keys:
        print(f"Already subscribed: {args.stream_id}")
    else:
        subscriptions.append(subscription)
        save_subscriptions(args.root, config)
        print(f"Subscribed: {args.stream_id}")

    if args.no_fetch:
        fetch.regenerate_catalog(args.root)
        return 0
    return fetch.main(["--root", str(args.root), "--once", args.stream_id])


def cmd_unsubscribe(args: argparse.Namespace) -> int:
    config = active_subscriptions(args.root)
    subscriptions = config.get("subscriptions") or []
    params = parse_params(args.parameters)
    matches = [
        subscription
        for subscription in subscriptions
        if subscription.get("id") == args.stream_id
        and all((subscription.get("parameters") or {}).get(key) == value for key, value in params.items())
    ]
    if not matches:
        print(f"No matching subscription: {args.stream_id}", file=sys.stderr)
        return 1
    if len(matches) > 1 and not args.all_matching:
        print(
            f"{len(matches)} subscriptions match {args.stream_id}; pass parameters or --all-matching",
            file=sys.stderr,
        )
        return 2

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
    print(f"Unsubscribed: {args.stream_id}" + (f" ({len(matches)} removed)" if len(matches) > 1 else ""))
    return 0


def state_status(root: Path, subscription: dict, defaults: dict) -> dict:
    stream = stream_summary(root, subscription["id"])
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
        "parameters": subscription.get("parameters") or {},
        "title": stream.get("title"),
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
        print(f"{label}: {freshness}, {exists}, updated={row['last_updated'] or 'never'}")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.all:
        return fetch.main(["--root", str(args.root), "--all"])
    if not args.stream_id:
        print("refresh requires a stream id or --all", file=sys.stderr)
        return 2
    return fetch.main(["--root", str(args.root), "--stream", args.stream_id])


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
    subscribe.add_argument("stream_id")
    subscribe.add_argument("parameters", nargs="*", help="stream parameters as key=value")
    subscribe.add_argument("--poll-interval-seconds", type=int)
    subscribe.add_argument("--history-limit", type=int)
    subscribe.add_argument("--no-fetch", action="store_true")
    subscribe.set_defaults(func=cmd_subscribe)

    unsubscribe = subparsers.add_parser("unsubscribe", help="remove a subscription")
    unsubscribe.add_argument("stream_id")
    unsubscribe.add_argument("parameters", nargs="*", help="match parameters as key=value")
    unsubscribe.add_argument("--all-matching", action="store_true")
    unsubscribe.add_argument("--keep-state", action="store_true")
    unsubscribe.set_defaults(func=cmd_unsubscribe)

    refresh = subparsers.add_parser("refresh", help="refresh subscriptions")
    refresh.add_argument("stream_id", nargs="?")
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
