# Agent Feeds

Agent Feeds is a small local protocol for giving an AI agent ambient awareness of subscribed external data streams through files.

This repository currently contains the v0.3 reference skeleton:

- `bundle/` contains the agent skill and command entrypoints.
- `catalog/` contains starter stream definitions and schemas.
- `scripts/` contains catalog build and validation helpers.
- `tests/` contains the initial test scaffold.
- `SPEC.md` is the implementation spec.

## Development

Install development dependencies:

```bash
uv sync
```

Build the catalog index:

```bash
uv run python scripts/build-index.py
```

Validate a stream:

```bash
uv run python scripts/validate-stream.py catalog/streams/weather/openmeteo-current.yaml
```

Run tests:

```bash
uv run pytest
```

## Use In Codex

Install the skill and fetcher from this checkout:

```bash
mkdir -p ~/.codex/skills ~/.local/bin
ln -sfn "$PWD/bundle" ~/.codex/skills/agentfeeds
cat > ~/.local/bin/agentfeeds-fetch <<EOF
#!/usr/bin/env bash
exec uv run --project "$PWD" "$PWD/bundle/bin/agentfeeds-fetch" "\$@"
EOF
chmod +x ~/.local/bin/agentfeeds-fetch
```

Start a new Codex session, then ask Codex to use the `agentfeeds` skill.

For a direct smoke test, create a subscription and fetch once:

```bash
mkdir -p ~/.agentfeeds
cat > ~/.agentfeeds/subscriptions.yaml <<'YAML'
version: "0.3"
defaults:
  poll_interval_seconds: 600
  history_limit: 50
subscriptions:
  - id: weather/openmeteo-current
    parameters:
      lat: 37.33
      lon: -121.89
YAML

agentfeeds-fetch --once weather/openmeteo-current
```

Then inspect `~/.agentfeeds/catalog.md` and the state file it lists.

Install background polling:

```bash
uv run bundle/bin/agentfeeds-install-poll
```

On macOS this installs a LaunchAgent at `~/Library/LaunchAgents/dev.agentfeeds.fetch.plist`. On Linux it installs a tagged crontab block. The interval is the shortest configured subscription interval, floored at 5 minutes.

Uninstall background polling:

```bash
uv run bundle/bin/agentfeeds-uninstall-poll
```

## Use In Hermes

Install the Hermes plugin from this checkout:

```bash
mkdir -p ~/.hermes/plugins
ln -sfn "$PWD/integrations/hermes/agentfeeds" ~/.hermes/plugins/agentfeeds
hermes plugins enable agentfeeds
```

Restart Hermes afterward. The plugin injects only compact stream metadata on each turn, for example:

```text
<agentfeeds>
Available local streams:
- weather/openmeteo-current: Current weather conditions (Open-Meteo)
- dev/hackernews-frontpage: Hacker News front page

When relevant, read ~/.agentfeeds/catalog.md to locate the state file before web search.
</agentfeeds>
```

## Status

The fetcher supports the v0.3 adapter kinds, subscription polling, state writes, event merging, local catalog cache updates, `catalog.md` regeneration, and local background polling installation.
