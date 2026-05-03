"""Adapter registry for Agent Feeds streams."""

from __future__ import annotations

from agentfeeds.adapters.http import fetch_json
from agentfeeds.adapters.ical import fetch_ical
from agentfeeds.adapters.local_command import fetch_local_command
from agentfeeds.adapters.local_file import fetch_local_file
from agentfeeds.adapters.rss import fetch_rss


def run_adapter(stream: dict, parameters: dict, *, validate_parameters, source_uri_for, substitute) -> tuple[str, list[dict]]:
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
    if kind == "local_command":
        return stream_uri, fetch_local_command(stream, adapter, stream_uri)
    raise ValueError(f"unsupported adapter kind: {kind}")
