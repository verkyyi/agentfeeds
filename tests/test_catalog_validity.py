from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-stream.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_stream", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_all_streams_validate():
    validator = load_validator()
    for path in sorted((ROOT / "catalog" / "streams").glob("**/*.yaml")):
        validator.validate_stream(path)


def test_index_matches_stream_count():
    index = json.loads((ROOT / "catalog" / "INDEX.json").read_text(encoding="utf-8"))
    streams = sorted((ROOT / "catalog" / "streams").glob("**/*.yaml"))
    assert index["stream_count"] == len(streams)
