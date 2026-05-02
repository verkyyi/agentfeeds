#!/usr/bin/env python3
"""Validate one Agent Feeds stream definition."""

from __future__ import annotations

import argparse
from pathlib import Path

from agentfeeds import fetch


def validate_stream(path: Path) -> None:
    fetch.validate_stream_file(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream", type=Path)
    args = parser.parse_args()
    validate_stream(args.stream)
    print(f"valid: {args.stream}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
