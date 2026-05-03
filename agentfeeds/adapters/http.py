"""HTTP JSON adapters."""

from __future__ import annotations

import requests

from agentfeeds.adapters.common import envelope, jmespath_search, stable_hash
from agentfeeds.constants import REQUEST_TIMEOUT_SECONDS


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
