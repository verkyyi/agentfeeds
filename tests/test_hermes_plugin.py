from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "hermes" / "agentfeeds" / "__init__.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("agentfeeds_hermes_plugin", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_hermes_plugin_injects_compact_stream_metadata(tmp_path):
    plugin = load_plugin()
    state_dir = tmp_path / "state" / "example.com"
    state_dir.mkdir(parents=True)
    (state_dir / "feed.json").write_text(
        json.dumps(
            {
                "_meta": {
                    "subscription_id": "example/feed",
                    "title": "Example feed",
                    "stale": False,
                },
                "data": {},
            }
        ),
        encoding="utf-8",
    )
    plugin.STATE_ROOT = tmp_path / "state"

    context = plugin._agentfeeds_context()["context"]

    assert "- example/feed: Example feed" in context
    assert "state/example.com/feed.json" not in context
    assert "stale" not in context
