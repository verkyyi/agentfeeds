# Changelog

## skill-v0.1.2 — 2026-05-04

Release: https://github.com/verkyyi/agentfeeds/releases/tag/skill-v0.1.2

Highlights:

- `setup.py` detects when `python3` on PATH is older than 3.11 and provisions a compatible interpreter via `uv`.
- Added `--python` setup override and rebuilds stale runtime virtualenvs on re-run.
- Bundled `dev/github-prs` and `dev/github-issues` templates now ship with `auth_service: github` / `auth: bearer_token`, so private repos work with a token at `~/.agentfeeds/secrets/github_token.txt`.

Validation:

- 50 unit tests pass; 9 pre-existing failures are unchanged from v0.1.1.
- Bundle manually inspected to confirm both fixes ship.

## skill-v0.1.1 — 2026-05

Initial public skill-bundle release for AgentFeeds.

Included:

- Agent-facing `SKILL.md` and references.
- Bundled Python runtime and CLI scripts.
- Frozen built-in template catalog fallback.
- Background polling installer for launchd/cron.
- Built-in templates for macOS personal sources, local files/directories/Markdown/Git state, RSS, GitHub, ICS calendars, weather, exchange rates, and approved local commands.
