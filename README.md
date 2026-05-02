# Agent Feeds

Agent Feeds is a small local protocol for giving an AI agent ambient awareness of subscribed external data streams through files.

This repository currently contains the v0.3 reference implementation:

- `agentfeeds/` contains the Python fetcher and polling entrypoints.
- `bundle/` contains the agent skill and command entrypoints.
- `catalog/` contains starter stream definitions and schemas.
- `integrations/hermes/agentfeeds/` contains the Hermes plugin, skill, and CLI wrappers.
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
ln -sfn "$PWD/integrations/hermes/agentfeeds/bin/agentfeeds" ~/.local/bin/agentfeeds
ln -sfn "$PWD/integrations/hermes/agentfeeds/bin/agentfeeds-fetch" ~/.local/bin/agentfeeds-fetch
```

Start a new Codex session, then ask Codex to use the `agentfeeds` skill.

For a direct smoke test, create a subscription and fetch once:

```bash
agentfeeds subscribe weather/openmeteo-current lat=37.33 lon=-121.89 --id weather/san-jose-current --title "San Jose current weather"
agentfeeds status
```

Then inspect `~/.agentfeeds/catalog.md` and the state file it lists.

Catalog entries are providers/templates. Active subscriptions are concrete instances:

- `provider` points to the catalog stream implementation.
- `id` is the concrete subscription shown to agents and used for refresh/unsubscribe.
- `--id` and `--title` can override the generated instance identity.

Manage subscriptions:

```bash
agentfeeds discover weather
agentfeeds list
agentfeeds subscribe dev/hackernews-frontpage
agentfeeds subscribe news/rss-generic url=https://openai.com/news/rss.xml --title "OpenAI News"
agentfeeds subscribe local/file path=~/notes/project.md --title "Project notes"
agentfeeds unsubscribe dev/hackernews-frontpage
agentfeeds refresh news/openai-com
agentfeeds refresh --all
agentfeeds status --json
```

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

Install the Hermes plugin, skill, and CLI wrappers from this checkout:

```bash
./integrations/hermes/agentfeeds/install.sh
```

For a GitHub install:

```bash
git clone https://github.com/verkyyi/agentfeeds ~/.hermes/plugins-src/agentfeeds
~/.hermes/plugins-src/agentfeeds/integrations/hermes/agentfeeds/install.sh
```

The installer:

- symlinks the plugin to `~/.hermes/plugins/agentfeeds`
- symlinks the skill to `~/.hermes/skills/agentfeeds`
- symlinks CLI wrappers to `~/.local/bin`
- enables the Hermes plugin
- initializes `~/.agentfeeds/catalog.md`

Restart Hermes afterward. The plugin injects only compact stream metadata on each turn, for example:

```text
<agentfeeds>
Available local streams:
- weather/san-jose-current: San Jose current weather
- dev/hackernews-frontpage: Hacker News front page

When relevant, read ~/.agentfeeds/catalog.md to locate the state file before web search.
</agentfeeds>
```

### Hermes Operator UX

Hermes operators should not need to use the CLI directly. Treat the CLI as Hermes' internal control plane: the operator asks for an outcome, Hermes discovers providers, subscribes, refreshes, reads state files, and reports the result.

Examples:

```text
What Agent Feeds providers can I subscribe to?
Subscribe my project notes at ~/notes/project.md as Project notes.
Refresh Project notes and tell me what changed.
Can Agent Feeds subscribe to my SQLite task database? If not, draft a provider.
```

Expected Hermes behavior:

- Use `agentfeeds discover <query>` internally to find providers.
- Use `agentfeeds subscribe ...` internally to materialize subscriptions.
- Use `agentfeeds refresh <subscription-id>` before answering when freshness matters.
- Read `~/.agentfeeds/catalog.md` and state JSON files before searching the web.
- Offer to draft a provider when no existing provider fits.
- Report outcomes and file locations, not raw CLI instructions, unless the operator asks for them.

### Hermes Provider Authoring

The Hermes skill can help operators draft new providers when `agentfeeds discover <query>` does not find a fit. Provider definitions live under `catalog/streams/`, schemas live under `catalog/schemas/event-types/`, and every provider should pass:

```bash
uv run python scripts/validate-stream.py catalog/streams/<category>/<name>.yaml
uv run python scripts/build-index.py
uv run pytest
```

For personal agents, prefer local/private read-only providers first, such as `local/file`, before adding public feeds.

## Status

The fetcher supports the v0.3 adapter kinds, subscription polling, state writes, event merging, local catalog cache updates, `catalog.md` regeneration, and local background polling installation.
