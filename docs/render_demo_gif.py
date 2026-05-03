#!/usr/bin/env python3
"""Render the Agent Feeds launch interactive-session demo GIF."""

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
BLUE = "#9cc9ff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size, index=0)
    return ImageFont.load_default()

TITLE = font(34, True)
SUB = font(20)
MONO = font(22)
SMALL = font(18)


def wrap_lines(text: str, width: int = 82) -> list[str]:
    lines: list[str] = []
    for raw in text.strip("\n").splitlines():
        if not raw:
            lines.append("")
        elif raw.startswith("  ") or raw.startswith("- ") or raw.startswith("<") or raw.startswith("</"):
            lines.append(raw)
        else:
            lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
    return lines


def line_color(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("User:"):
        return GREEN
    if stripped.startswith("Hermes:"):
        return YELLOW
    if stripped.startswith("<agentfeeds>") or stripped.startswith("</agentfeeds>"):
        return CYAN
    if stripped.startswith("-"):
        return BLUE
    if "agentfeeds streams read" in line or "before web search" in line:
        return PINK
    if "fresh" in line.lower() or "local state" in line.lower() or "without web search" in line.lower():
        return CYAN
    return TEXT


def frame(title: str, subtitle: str, body: str, highlight: str = "") -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

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

    y = 222
    for line in wrap_lines(body):
        color = line_color(line)
        active_font = MONO if line.strip().startswith(("User:", "Hermes:", "<", "</")) or line.strip().startswith("-") else SMALL
        d.text((84, y), line, fill=color, font=active_font)
        y += 27 if active_font == MONO else 24

    if highlight:
        d.rounded_rectangle((82, H - 112, W - 82, H - 72), radius=12, fill="#112942", outline="#2f6f9f", width=1)
        d.text((104, H - 103), highlight, fill=CYAN, font=SUB)
    return img


SCENES = [
    (
        "Agent Feeds in a Hermes session",
        "The demo is the agent experience, not the CLI.",
        "A new Hermes session can inspect a compact list of available local streams.\n\nThe user just asks normal questions. Hermes chooses when to run agentfeeds streams read before web search.",
        "Agents need feeds: fresh local state, read only when relevant.",
        3600,
    ),
    (
        "Session context injected once",
        "Only a compact map enters the prompt; detailed state stays on disk.",
        "agentfeeds streams list\n- weather/santa-clara-current: Santa Clara current weather\n- dev/hackernews-frontpage: Hacker News front page\n- finance/quote-btc: BTC quote\n- news/openai-com: OpenAI News\n- ops/hermes-gateway-health: Hermes gateway health\n\nWhen relevant, run agentfeeds streams read <subscription-id> --json before web search.",
        "Compact metadata in prompt. Bulky JSON remains local.",
        5200,
    ),
    (
        "Use case: current news without web search",
        "The user asks naturally; Hermes sees a matching active stream.",
        "User: What is on Hacker News right now?\n\nHermes: I see a fresh Hacker News front page stream. I’ll run agentfeeds streams read first instead of searching the web.\n\nHermes: Here are the top stories from the local HN snapshot, with scores and links.",
        "Fresh answers from local state.",
        4300,
    ),
    (
        "Use case: personal ops awareness",
        "Streams can cover private/local status, not just public feeds.",
        "User: Is my Hermes gateway healthy?\n\nHermes: There is an ops/hermes-gateway-health stream. I’ll inspect it with agentfeeds streams read.\n\nHermes: Gateway is healthy; latest check is fresh. If it were stale, I would refresh that stream before answering.",
        "The agent can monitor local/private systems conversationally.",
        4300,
    ),
    (
        "Use case: market and weather snapshots",
        "Snapshot streams answer quick factual questions without repeated setup.",
        "User: What are BTC and MSFT doing, and what is Santa Clara weather?\n\nHermes: I see subscribed quote and weather streams. I’ll read the relevant local snapshots and summarize them together.\n\nHermes: Answer is grounded in timestamped Agent Feeds state, not chat memory.",
        "Feeds are timestamped current context, not durable memory.",
        4500,
    ),
    (
        "Use case: followed AI sources",
        "RSS/release streams keep the agent aware of sources the operator cares about.",
        "User: Anything new from OpenAI, Anthropic, or Hermes Agent releases?\n\nHermes: I see active streams for OpenAI News, Anthropic RSS, and NousResearch/hermes-agent releases. I’ll read those local event files and report what changed.\n\nHermes: No need to paste URLs or restate which sources matter.",
        "The session starts already oriented around your subscribed world.",
        5000,
    ),
    (
        "Why this matters",
        "Agent Feeds is the ambient context layer between memory and tools.",
        "Memory: durable facts about the user.\nFeeds: fresh, timestamped state around the user.\nTools: actions the agent can run when needed.\n\nAgent Feeds lets Hermes answer from local/private state first, while keeping the data path inspectable through the streams CLI.",
        "Not memory. Not prompt stuffing. Fresh inspectable feeds.",
        5000,
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
