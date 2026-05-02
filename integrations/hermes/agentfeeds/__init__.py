"""Hermes plugin for compact Agent Feeds metadata injection."""

from __future__ import annotations

import json
from pathlib import Path


STATE_ROOT = Path.home() / ".agentfeeds" / "state"
MAX_STREAMS = 20


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
    entries = _stream_entries()
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
