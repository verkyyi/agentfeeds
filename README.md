# Agent Feeds

Agent Feeds gives Hermes local ambient awareness through refreshable file-based streams.

It is a local-first context layer for personal agents. Instead of asking you to run commands, Hermes can use Agent Feeds as an internal control plane: discover providers, subscribe to sources, refresh state, read local snapshots/events, and report the result in conversation.

Agent Feeds is not long-term memory. It is a small, inspectable substrate for fresh context that lives on your machine.

## Why It Exists

Personal agents need awareness of local and private state without stuffing every detail into the prompt or reaching for web search first.

Agent Feeds keeps the heavy data on disk:

- compact stream metadata is injected into Hermes
- detailed JSON state is read only when relevant
- background refresh keeps subscriptions warm
- providers can be public feeds, local files, or operator-approved local commands

This makes the agent context-aware while keeping the data path visible and debuggable.

## What You Can Ask

```text
What Agent Feeds providers can I subscribe to?
Subscribe my project notes at ~/notes/project.md as Project notes.
Refresh Project notes and tell me what changed.
Subscribe me to Hacker News front page.
Subscribe me to OpenAI News from https://openai.com/news/rss.xml.
Can Agent Feeds subscribe to my SQLite task database? If not, draft a provider.
```

Hermes should handle the details. You should not need to know provider IDs, subscription IDs, or CLI flags unless you explicitly ask for them.

## Install For Hermes

From this checkout:

```bash
./integrations/hermes/agentfeeds/install.sh
```

From GitHub:

```bash
git clone https://github.com/verkyyi/agentfeeds ~/.hermes/plugins-src/agentfeeds
~/.hermes/plugins-src/agentfeeds/integrations/hermes/agentfeeds/install.sh
```

The installer:

- symlinks the Hermes plugin to `~/.hermes/plugins/agentfeeds`
- symlinks the Hermes skill to `~/.hermes/skills/agentfeeds`
- installs Agent Feeds command wrappers in `~/.local/bin`
- enables the Hermes plugin
- initializes `~/.agentfeeds/catalog.md`

Restart Hermes after installation.

## How It Works

Agent Feeds stores its local state under `~/.agentfeeds/`:

- `subscriptions.yaml` is the source of truth for active subscriptions.
- `catalog.md` is the compact summary Hermes reads to find relevant state files.
- `state/` contains JSON snapshots for subscribed sources.

The Hermes plugin injects only compact stream metadata into the prompt:

```text
<agentfeeds>
Available local streams:
- local/project-notes-md: Project notes
- dev/hackernews-frontpage: Hacker News front page

When relevant, read ~/.agentfeeds/catalog.md to locate the state file before web search.
</agentfeeds>
```

Full data stays on disk and is read only when relevant.

## Demo Flow

After installing the Hermes integration, ask Hermes:

```text
What Agent Feeds providers can I subscribe to?
Subscribe me to Hacker News front page.
Show me the current Hacker News front page from Agent Feeds.
```

Or inspect the same flow directly:

```bash
agentfeeds discover hacker
agentfeeds subscribe dev/hackernews-frontpage
agentfeeds status
cat ~/.agentfeeds/catalog.md
```

For a private local source:

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
Refresh Project notes and summarize it.
```

## Built-In Providers

Current built-ins:

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

Catalog entries are providers/templates. Active subscriptions are concrete instances. For example, `news/rss-generic` can become `news/openai-com`, and `local/file` can become `local/project-notes-md`.

## Background Refresh

Install background polling when you want subscriptions to stay warm without waiting for Hermes to refresh them during a conversation:

```bash
agentfeeds-install-poll
```

Uninstall it with:

```bash
agentfeeds-uninstall-poll
```

On macOS this installs a LaunchAgent at `~/Library/LaunchAgents/dev.agentfeeds.fetch.plist`. On Linux it installs a tagged crontab block. The interval is the shortest configured subscription interval, floored at 5 minutes.

## Provider Authoring

If no built-in provider fits, ask Hermes to draft one:

```text
Can Agent Feeds subscribe to my local SQLite task database? If not, draft a provider.
```

Hermes should:

- check existing providers first
- draft provider YAML under `~/.agentfeeds/providers/streams/`
- draft or reuse a schema under `~/.agentfeeds/providers/schemas/event-types/`
- validate the provider with `agentfeeds providers validate`
- test it once with `agentfeeds providers test <provider-id> key=value`
- smoke-test it with a temporary Agent Feeds root before touching your live subscriptions

Command-based providers are supported through `local_command`, but Hermes should only create them for commands you explicitly approve. They run without a shell, with timeout and output limits. They can capture one command snapshot or parse JSON output into event items.

For personal agents, prefer local/private read-only providers before adding public feeds.

## Manual Inspection

You can inspect Agent Feeds directly when needed:

```bash
agentfeeds list
agentfeeds status
agentfeeds discover local
agentfeeds providers adapters
agentfeeds providers list
agentfeeds providers path
agentfeeds providers scaffold json_http personal/tasks
agentfeeds providers test personal/tasks url=https://example.com/tasks.json
agentfeeds providers validate
```

These commands are mainly for debugging. The normal UX is to ask Hermes for the outcome you want.

## Sharing

See [docs/SHARING.md](docs/SHARING.md) for a short pitch, demo script, and release notes draft.

For product framing, use cases, and benefits, see [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).
