from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml


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
    (tmp_path / "subscriptions.yaml").write_text(
        yaml.safe_dump(
            {
                "subscriptions": [
                    {
                        "id": "example/feed",
                        "title": "Example feed",
                        "provider": "example/provider",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    plugin.STATE_ROOT = tmp_path / "state"
    plugin.SUBSCRIPTIONS_FILE = tmp_path / "subscriptions.yaml"

    context = plugin._agentfeeds_context()["context"]

    assert "- example/feed: Example feed" in context
    assert "state/example.com/feed.json" not in context
    assert "stale" not in context


def test_hermes_plugin_falls_back_to_state_metadata(tmp_path):
    plugin = load_plugin()
    state_dir = tmp_path / "state" / "example.com"
    state_dir.mkdir(parents=True)
    (state_dir / "feed.json").write_text(
        json.dumps({"_meta": {"subscription_id": "example/feed", "title": "Example feed"}, "data": {}}),
        encoding="utf-8",
    )
    plugin.STATE_ROOT = tmp_path / "state"
    plugin.SUBSCRIPTIONS_FILE = tmp_path / "missing.yaml"

    context = plugin._agentfeeds_context()["context"]

    assert "- example/feed: Example feed" in context
