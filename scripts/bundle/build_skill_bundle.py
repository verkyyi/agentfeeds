#!/usr/bin/env python3
"""Build a clean Agent Feeds skill bundle for release artifacts."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


INCLUDE_PATHS = [
    "SKILL.md",
    "LICENSE",
    "agents",
    "assets",
    "catalog",
    "references",
    "scripts",
    "pyproject.toml",
]
EXCLUDE_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "bundle",
    "evals",
}
EXCLUDE_NAMES = {
    "publishing.md",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in path.parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    if any(part.endswith(".egg-info") for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def iter_bundle_files(root: Path):
    for item in INCLUDE_PATHS:
        path = root / item
        if not path.exists():
            continue
        if path.is_file():
            if should_include(path.relative_to(root)):
                yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and should_include(child.relative_to(root)):
                yield child


def build_bundle(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in iter_bundle_files(root):
            archive.write(path, path.relative_to(root))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Agent Feeds skill bundle")
    parser.add_argument("--output", type=Path, default=Path("dist") / "agentfeeds-skill.zip")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    build_bundle(root, args.output)
    print(f"wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
