from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL_FILES = [
    ROOT / "SKILL.md",
    *sorted((ROOT / "references").glob("*.md")),
]
HOST_SPECIFIC_TERMS = {
    "Hermes",
    "Claude",
    "Cursor",
    "OpenClaw",
}


def test_canonical_skill_instructions_are_host_agnostic():
    for path in CANONICAL_SKILL_FILES:
        text = path.read_text(encoding="utf-8")
        for term in HOST_SPECIFIC_TERMS:
            assert term not in text, f"{path.relative_to(ROOT)} should not mention host-specific term {term!r}"
