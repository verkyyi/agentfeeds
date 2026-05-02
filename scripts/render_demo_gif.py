#!/usr/bin/env python3
"""Render the Agent Feeds launch terminal demo GIF."""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "agentfeeds-demo.gif"
W, H = 1280, 720
BG = "#071019"
PANEL = "#0d1724"
BORDER = "#1f3b55"
TEXT = "#d7e7f7"
MUTED = "#7f95aa"
GREEN = "#83e6a6"
CYAN = "#78dce8"
YELLOW = "#ffd166"
PINK = "#ff7eb6"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size, index=0)
    return ImageFont.load_default()

TITLE = font(34, True)
SUB = font(20)
MONO = font(24)
SMALL = font(19)


def wrap_lines(text: str, width: int = 78) -> list[str]:
    lines: list[str] = []
    for raw in text.strip("\n").splitlines():
        if not raw:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
    return lines


def frame(title: str, subtitle: str, body: str, highlight: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # soft data-grid background
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill="#0a1723")
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill="#0a1723")

    d.rounded_rectangle((54, 44, W - 54, H - 44), radius=24, fill=PANEL, outline=BORDER, width=2)
    d.ellipse((82, 72, 98, 88), fill="#ff5f57")
    d.ellipse((108, 72, 124, 88), fill="#ffbd2e")
    d.ellipse((134, 72, 150, 88), fill="#28c840")

    d.text((82, 114), title, fill=TEXT, font=TITLE)
    d.text((84, 158), subtitle, fill=MUTED, font=SUB)
    d.line((82, 196, W - 82, 196), fill=BORDER, width=2)

    y = 226
    for line in wrap_lines(body, width=74):
        color = TEXT
        if line.startswith("$"):
            color = GREEN
        elif line.startswith("#") or line.startswith("##"):
            color = CYAN
        elif "Subscribed:" in line or "fresh, ok" in line or "Stale: no" in line:
            color = GREEN
        elif "Hermes" in line or "local JSON" in line or "before web search" in line:
            color = YELLOW
        elif "not" in line.lower() and ("memory" in line.lower() or "prompt" in line.lower()):
            color = PINK
        d.text((84, y), line, fill=color, font=MONO if line.startswith("$") else SMALL)
        y += 30 if line.startswith("$") else 25

    if highlight:
        d.rounded_rectangle((82, H - 112, W - 82, H - 72), radius=12, fill="#112942", outline="#2f6f9f", width=1)
        d.text((104, H - 103), highlight, fill=CYAN, font=SUB)
    return img


SCENES = [
    (
        "Agent Feeds",
        "Local-first ambient context streams for Hermes and personal agents",
        "Agents often start sessions blind. Users repeat context, paste big prompt blobs, or make the agent re-search state that could already be fresh locally.\n\nAgent Feeds keeps subscriptions and JSON state under ~/.agentfeeds, then gives Hermes only a compact catalog.",
        "Agents need feeds, not just memory.",
        1800,
    ),
    (
        "1. Discover providers",
        "The operator asks for outcomes; the CLI is the inspectable control plane.",
        "$ agentfeeds discover hacker\n\ndev/hackernews-frontpage: Hacker News front page [params: none, mode: event]",
        "Find a stream the agent can subscribe to.",
        1500,
    ),
    (
        "2. Subscribe to public state",
        "Subscriptions become concrete active context, not generic templates.",
        "$ agentfeeds subscribe dev/hackernews-frontpage --title \"Hacker News front page\"\n\nSubscribed: dev/hackernews-frontpage (Hacker News front page)",
        "Background refresh can keep this warm.",
        1500,
    ),
    (
        "3. Subscribe to private local state",
        "Local files let a personal agent inspect project context without prompt stuffing.",
        "$ agentfeeds subscribe local/file path=~/notes/project.md \\\n    --id local/project-notes-md \\\n    --title \"Project notes\"\n\nSubscribed: local/project-notes-md (Project notes)",
        "Private context stays on the machine.",
        1700,
    ),
    (
        "4. Check active streams",
        "The status view shows freshness and whether each fetch is healthy.",
        "$ agentfeeds status\n\ndev/hackernews-frontpage: Hacker News front page, fresh, ok\nlocal/project-notes-md path=~/notes/project.md: Project notes, fresh, ok",
        "Freshness is explicit, not guessed from chat history.",
        1700,
    ),
    (
        "5. Hermes sees a compact catalog",
        "Detailed data stays in state files until relevant.",
        "$ sed -n '1,80p' ~/.agentfeeds/catalog.md\n\n# Agent Feeds - Active Subscriptions\n\n## Hacker News front page\n- ID: dev/hackernews-frontpage\n- Path: state/hn.algolia.com/frontpage.json\n- Stale: no\n\n## Project notes\n- ID: local/project-notes-md\n- Path: state/local.file/file.project.md.<hash>.json\n- Stale: no",
        "Compact prompt metadata; bulky JSON on disk.",
        2300,
    ),
    (
        "6. Answer from local state",
        "When relevant, Hermes reads the right state file before using web search.",
        "$ Ask Hermes: \"What is on Hacker News right now from Agent Feeds?\"\n\nHermes reads ~/.agentfeeds/catalog.md, locates state/hn.algolia.com/frontpage.json, and answers from local JSON state before web search.",
        "Not memory. Not prompt stuffing. Fresh inspectable feeds.",
        2300,
    ),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for title, subtitle, body, highlight, duration in SCENES:
        img = frame(title, subtitle, body, highlight)
        frames.append(img)
        durations.append(duration)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(OUT)


if __name__ == "__main__":
    main()
