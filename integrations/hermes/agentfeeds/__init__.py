"""Hermes plugin for compact Agent Feeds metadata injection."""

from __future__ import annotations

import json
from pathlib import Path

STATE_ROOT = Path.home() / ".agentfeeds" / "state"
SUBSCRIPTIONS_FILE = Path.home() / ".agentfeeds" / "subscriptions.yaml"
MAX_STREAMS = 20


def _clean_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _subscription_entries() -> list[dict]:
    if not SUBSCRIPTIONS_FILE.exists():
        return []
    try:
        lines = SUBSCRIPTIONS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    entries = []
    current = {}
    in_subscriptions = False
    for line in lines:
        if line.strip() == "subscriptions:":
            in_subscriptions = True
            continue
        if not in_subscriptions:
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current.get("id") and current.get("title"):
                entries.append({"id": current["id"], "title": current["title"]})
            current = {}
            item = stripped[2:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = _clean_yaml_scalar(value)
            continue
        if current and line.startswith(("  ", "    ")) and ":" in line:
            key, value = stripped.split(":", 1)
            if key in {"id", "title"}:
                current[key] = _clean_yaml_scalar(value)
    if current.get("id") and current.get("title"):
        entries.append({"id": current["id"], "title": current["title"]})
    return entries[:MAX_STREAMS]


def _stream_entries() -> list[dict]:
    if not STATE_ROOT.exists():
        return []

    entries = []
    for path in sorted(STATE_ROOT.glob("**/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = payload.get("_meta") or {}
        stream_id = meta.get("subscription_id")
        title = meta.get("title") or meta.get("type")
        if not stream_id or not title:
            continue
        entries.append(
            {
                "id": str(stream_id),
                "title": str(title),
            }
        )
    return entries[:MAX_STREAMS]


def _agentfeeds_context(**_kwargs):
    entries = _subscription_entries() or _stream_entries()
    if not entries:
        return None

    lines = ["<agentfeeds>", "Available local streams:"]
    lines.extend(f"- {entry['id']}: {entry['title']}" for entry in entries)
    lines.extend(
        [
            "",
            "When relevant, read ~/.agentfeeds/catalog.md to locate the state file before web search.",
            "</agentfeeds>",
        ]
    )
    return {"context": "\n".join(lines)}


def register(ctx):
    ctx.register_hook("pre_llm_call", _agentfeeds_context)
