# Agent Feeds

Agent Feeds is a local-first ambient context layer for Hermes and personal agents.

Personal agents often start sessions blind: users repeat project context, paste large prompt blobs, or make the agent re-search/re-run commands for state that could already be cached locally. Agent Feeds fixes that with refreshable subscriptions, compact prompt metadata, and inspectable JSON state on disk.

**Agents need feeds, not just memory.** Memory is for durable facts. Feeds are for fresh, timestamped state: repo issues, project notes, RSS/news, calendars, weather, local dashboards, or approved local command output.

## Quick Demo

![Agent Feeds interactive session demo](assets/agentfeeds-demo.gif)

Install the standalone Hermes plugin:

```bash
git clone https://github.com/verkyyi/agentfeeds-hermes-plugin ~/.hermes/plugins-src/agentfeeds-hermes-plugin
~/.hermes/plugins-src/agentfeeds-hermes-plugin/install.sh
```

Restart Hermes, then try one prompt at a time:

```text
What Agent Feeds templates can I subscribe to?
```

```text
Subscribe me to Hacker News front page.
```

```text
Show me the current Hacker News front page from Agent Feeds.
```

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

```text
Refresh Project notes and summarize it.
```

What happens under the hood:

- `python scripts/agentfeeds.py` manages active subscriptions and template discovery
- `python scripts/agentfeeds_fetch.py` refreshes subscribed streams into local JSON state
- agents use `python scripts/agentfeeds.py streams ...` to list and read compact relevant data
- raw files stay inspectable for debugging, but they are not the normal agent interface

Agent Feeds is not long-term memory. It is a refreshable, local-first context layer for fresh, inspectable ambient context that lives on your machine.

This repository is also an agent-agnostic Agent Skill. Skills-compatible agents can load [SKILL.md](SKILL.md) for portable instructions on using the Agent Feeds CLI and subscribed stream data.

## Skill Runtime Setup

From this skill checkout, install the local Python runtime once:

```bash
python scripts/setup.py
```

Then agents can drive the bundled scripts directly:

```bash
python scripts/agentfeeds.py --help
python scripts/agentfeeds_fetch.py --help
```

## Why It Exists

Personal agents need awareness of local and private state without stuffing every detail into the prompt, rerunning expensive discovery, or reaching for web search first.

Agent Feeds keeps the heavy data on disk:

- compact stream metadata is injected into Hermes
- detailed JSON state is read only when relevant
- background refresh keeps subscriptions warm
- templates can be public feeds, local files, or operator-approved local commands

This makes the agent context-aware while keeping the data path visible and debuggable.

Agent Feeds also gives agents a small local control surface for discovering templates, subscribing to sources, refreshing state, reading local snapshots/events, and reporting the result in conversation.

## What You Can Ask

Each example is meant to be used as a single message to Hermes:

```text
What Agent Feeds templates can I subscribe to?
```

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

```text
Refresh Project notes and tell me what changed.
```

```text
Subscribe me to Hacker News front page.
```

```text
Subscribe me to OpenAI News from https://openai.com/news/rss.xml.
```

```text
Can Agent Feeds subscribe to my SQLite task database? If not, draft a template.
```

Hermes should handle the details. You should not need to know template IDs, subscription IDs, or CLI flags unless you explicitly ask for them.

## Install For Hermes

Use the standalone Hermes plugin repo:

```bash
git clone https://github.com/verkyyi/agentfeeds-hermes-plugin ~/.hermes/plugins-src/agentfeeds-hermes-plugin
~/.hermes/plugins-src/agentfeeds-hermes-plugin/install.sh
```

The installer:

- clones or updates Agent Feeds core under `~/.hermes/plugins-src/agentfeeds-core`
- clones or updates the built-in template catalog under `~/.hermes/plugins-src/agentfeeds-catalog`
- symlinks the Hermes plugin to `~/.hermes/plugins/agentfeeds`
- symlinks the Hermes skill to `~/.hermes/skills/agentfeeds`
- installs Agent Feeds command wrappers in `~/.local/bin`
- enables the Hermes plugin
- initializes the local Agent Feeds root

Restart Hermes after installation.

## How It Works

Agent Feeds stores local state under `~/.agentfeeds/`, but agents should normally drive it through the CLI:

- `python scripts/agentfeeds.py templates ...` discovers reusable feed definitions
- `python scripts/agentfeeds.py subscribe ...` creates active subscriptions
- `python scripts/agentfeeds.py streams ...` lists and reads refreshed data
- `python scripts/agentfeeds_fetch.py ...` refreshes subscriptions

Full data stays on disk and is read only when relevant. The storage layout remains inspectable, but it should be a debug and authoring surface rather than ambient prompt context.

## Demo Flow

After installing the Hermes plugin, ask Hermes one prompt at a time:

```text
What Agent Feeds templates can I subscribe to?
```

```text
Subscribe me to Hacker News front page.
```

```text
Show me the current Hacker News front page from Agent Feeds.
```

Or inspect the same flow directly:

```bash
python scripts/agentfeeds.py templates search hacker
python scripts/agentfeeds.py subscribe dev/hackernews-frontpage
python scripts/agentfeeds.py streams list
python scripts/agentfeeds.py streams read dev/hackernews-frontpage --json
```

For a private local source:

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

```text
Refresh Project notes and summarize it.
```

## Built-In Templates

Built-in template definitions live in the standalone catalog repo:

```text
https://github.com/verkyyi/agentfeeds-catalog
```

Current built-in templates include:

- `local/file`: read-only snapshot of one local text, Markdown, or JSON file
- `news/rss-generic`: RSS or Atom feed
- `dev/hackernews-frontpage`: Hacker News front page
- `dev/github-releases`: GitHub repository releases
- `dev/github-issues`: GitHub repository issues
- `dev/github-prs`: GitHub repository pull requests
- `calendar/ics`: public iCalendar feed
- `weather/openmeteo-current`: current weather by latitude/longitude
- `weather/openmeteo-forecast`: 7-day forecast by latitude/longitude
- `finance/exchangerate`: current exchange rates
- `geo/usgs-earthquakes-hour`: recent USGS earthquakes
- `space/iss-location`: current ISS location

Catalog entries are templates. Active subscriptions are concrete instances. For example, `news/rss-generic` can become `news/openai-com`, and `local/file` can become `local/project-notes-md`.

Catalog loading can be pointed at a local checkout or alternate raw source:

```bash
AGENTFEEDS_CATALOG_DIR=~/projects/agentfeeds-catalog python scripts/agentfeeds_fetch.py --update-catalog
AGENTFEEDS_CATALOG_BASE_URL=https://raw.githubusercontent.com/verkyyi/agentfeeds-catalog/main python scripts/agentfeeds_fetch.py --update-catalog
```

## Background Refresh

Install background polling when you want subscriptions to stay warm without waiting for Hermes to refresh them during a conversation:

```bash
python scripts/polling/install.py
```

Uninstall it with:

```bash
python scripts/polling/uninstall.py
```

On macOS this installs a LaunchAgent at `~/Library/LaunchAgents/dev.agentfeeds.fetch.plist`. On Linux it installs a tagged crontab block. The interval is the shortest configured subscription interval, floored at 5 minutes.

## Template Authoring

If no built-in template fits, ask Hermes to draft one:

```text
Can Agent Feeds subscribe to my local SQLite task database? If not, draft a template.
```

Agents should:

- check existing templates first
- draft template YAML under `~/.agentfeeds/templates/streams/`
- draft or reuse a schema under `~/.agentfeeds/templates/schemas/event-types/`
- validate the template with `python scripts/agentfeeds.py templates validate`
- test it once with `python scripts/agentfeeds.py templates test <template-id> key=value`
- smoke-test it with a temporary Agent Feeds root before touching your live subscriptions

Command-based templates are supported through `local_command`, but agents should only create them for commands you explicitly approve. They run without a shell, with timeout and output limits. They can capture one command snapshot or parse JSON output into event items.

For personal agents, prefer local/private read-only templates before adding public feeds.

## Manual Inspection

You can inspect Agent Feeds directly when needed:

```bash
python scripts/agentfeeds.py streams list
python scripts/agentfeeds.py streams search project
python scripts/agentfeeds.py templates search local
python scripts/agentfeeds.py templates adapters
python scripts/agentfeeds.py templates list
python scripts/agentfeeds.py templates path
python scripts/agentfeeds.py templates scaffold json_http personal/tasks
python scripts/agentfeeds.py templates test personal/tasks url=https://example.com/tasks.json
python scripts/agentfeeds.py templates validate
```

These commands are mainly for debugging. The normal UX is to ask Hermes for the outcome you want.

## FAQ

### Why not just use agent memory?

Memory is for durable facts that should survive across sessions. Agent Feeds is for fresh state that changes over time: feed items, repo issues, calendars, weather, dashboards, project notes, or command snapshots. The state is timestamped and refreshable instead of being mixed into chat history.

### Why not put everything in the prompt?

Large prompts are expensive, noisy, and stale. Agent Feeds injects only a compact catalog of available streams, then lets Hermes read detailed state only when the user asks something relevant.

### Why not a vector database?

Agent Feeds is not semantic recall. It is structured, inspectable current state. Subscriptions, template definitions, schemas, and JSON state are plain files under `~/.agentfeeds/` so operators can debug what the agent sees.

### Why not MCP?

MCP is a great tool interface. Agent Feeds is a local state substrate: background refresh, subscriptions, a compact catalog, and state files that agents can inspect across sessions. They can complement each other.

### Is this an RSS reader?

RSS is one template type. Agent Feeds also supports local files, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, and operator-approved local commands. The product is the subscription/state layer for agents, not a human feed UI.

## Sharing

See [docs/DEMO.md](docs/DEMO.md) for the demo transcript and talking points.

See [docs/SHARING.md](docs/SHARING.md) for a short pitch, demo script, and release notes draft.

For product framing, use cases, and benefits, see [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

For protocol and implementation details, see [docs/SPEC.md](docs/SPEC.md).
