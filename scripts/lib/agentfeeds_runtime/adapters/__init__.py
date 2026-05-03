"""Adapter registry for Agent Feeds streams."""

from __future__ import annotations

from agentfeeds_runtime.adapters.http import fetch_json
from agentfeeds_runtime.adapters.ical import fetch_ical
from agentfeeds_runtime.adapters.local_sources import fetch_local_directory, fetch_local_git_status, fetch_markdown_vault
from agentfeeds_runtime.adapters.local_command import fetch_local_command
from agentfeeds_runtime.adapters.local_file import fetch_local_file
from agentfeeds_runtime.adapters.mac_native import (
    fetch_finder_recent_downloads,
    fetch_imessage_sqlite,
    fetch_mac_calendar,
    fetch_mac_mail,
    fetch_mac_notes,
    fetch_mac_reminders,
    fetch_safari_reading_list,
)
from agentfeeds_runtime.adapters.rss import fetch_rss


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
    if kind == "local_directory":
        return stream_uri, fetch_local_directory(stream, adapter, stream_uri)
    if kind == "markdown_vault":
        return stream_uri, fetch_markdown_vault(stream, adapter, stream_uri)
    if kind == "local_git_status":
        return stream_uri, fetch_local_git_status(stream, adapter, stream_uri)
    if kind == "local_command":
        return stream_uri, fetch_local_command(stream, adapter, stream_uri)
    if kind == "mac_calendar":
        return stream_uri, fetch_mac_calendar(stream, adapter, stream_uri)
    if kind == "mac_reminders":
        return stream_uri, fetch_mac_reminders(stream, adapter, stream_uri)
    if kind == "mac_notes":
        return stream_uri, fetch_mac_notes(stream, adapter, stream_uri)
    if kind == "mac_mail":
        return stream_uri, fetch_mac_mail(stream, adapter, stream_uri)
    if kind == "imessage_sqlite":
        return stream_uri, fetch_imessage_sqlite(stream, adapter, stream_uri)
    if kind == "safari_reading_list":
        return stream_uri, fetch_safari_reading_list(stream, adapter, stream_uri)
    if kind == "finder_recent_downloads":
        return stream_uri, fetch_finder_recent_downloads(stream, adapter, stream_uri)
    raise ValueError(f"unsupported adapter kind: {kind}")
