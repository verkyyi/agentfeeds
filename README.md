# AgentFeeds

Ready-to-read fresh context for personal agents.

AgentFeeds keeps changing local and public context warm on disk — calendars, inboxes, reminders, GitHub, RSS/news, weather, finance, notes, dashboards, and approved local sources — so agents can check what is already fresh before scanning skills, searching the web, re-fetching APIs, or asking you to repeat context.

The primary audience for this repository is people building, operating, publishing, or auditing skill-based personal agents. The Python package and CLI are implementation details for the agent to drive.

## Why AgentFeeds

Agents waste time and tokens rediscovering where context lives. They may scan skills, search the web, call the same APIs, or ask the user to repeat information that could already be waiting locally.

AgentFeeds moves that work into background refresh plus an agent-facing read path:

- Faster answers: subscribed context is already refreshed and ready to read.
- Less repeated discovery: agents can search local streams before exploring skills or external sources.
- Cleaner memory: volatile state stays in feeds instead of long-term memory.
- Local and inspectable: stream state lives under `~/.agentfeeds/` and can be audited.
- Agent-facing UX: users prompt their agent; agents run the scripts.

## Agent Context Model

| Layer | Best for | Not for |
| --- | --- | --- |
| Memory | Durable facts, preferences, stable conventions | Today's inbox, latest issues, weather, dashboards |
| Skills | Teaching the agent how to do a workflow | Storing changing source data |
| Tools | One-off actions and live calls | Repeatedly rediscovering the same context |
| AgentFeeds | Ready-to-read fresh context from subscribed streams | Durable identity or preferences |

Agents need feeds, not just memory. Memory remembers stable facts. AgentFeeds keeps fresh context ready to read.

## How AgentFeeds Is Different

AgentFeeds is intentionally narrow: it is a refreshable local state layer for agents, not another all-purpose memory system.

- **Not memory:** durable preferences and identity still belong in memory; volatile state stays in timestamped feeds.
- **Not RAG:** streams are subscribed, structured, and refreshed on a schedule instead of being only semantically searched after the fact.
- **Not an MCP replacement:** MCP exposes tools; AgentFeeds keeps tool/API/local-source results warm on disk so an agent can inspect state before deciding what to call.
- **Not a dashboard:** humans can inspect the files, but the primary reader is the agent via `brief`, `search`, and `streams read`.

The practical promise is simple: before your personal agent searches the web, scans skills, re-fetches APIs, or asks you to repeat context, it can check what fresh local streams already exist.

## Trust And Safety Model

AgentFeeds is designed for local-first, inspectable operation:

- Stream state is stored as JSON under `~/.agentfeeds/`; operators can audit what the agent sees.
- Built-in public/API templates use explicit parameters and schemas, with a frozen catalog bundled for first-run reliability.
- Local command templates run without a shell, with argv arrays, timeouts, and output-size limits.
- New `local_command` templates are safety-gated: they do not execute until the operator approves the exact template and command digest interactively.
- Agents are instructed to use `subscribe`, `refresh`, and `streams read` instead of hand-writing state files.
- Secrets should be referenced through AgentFeeds secret slots, not committed into template YAML.

## Try It With Your Agent

After installing the skill, you should not need to operate AgentFeeds directly. Ask your agent for outcomes in natural language:

```text
Set up AgentFeeds with useful safe default streams for this agent.
```

```text
What fresh context does AgentFeeds already have available?
```

```text
Use AgentFeeds first. What should I pay attention to today?
```

```text
Subscribe AgentFeeds to my calendar, reminders, unread mail, GitHub activity, and a few AI news sources.
```

```text
Before searching the web, check AgentFeeds for relevant cached context.
```

The agent should handle template discovery, subscription setup, refreshes, health checks, and compact state reads through the bundled scripts. You should not need to know template IDs, subscription IDs, or CLI flags unless you ask for them.

## Example: First Stop For Fresh Context

Without AgentFeeds, a user asks:

```text
What should I pay attention to today?
```

The agent has to decide whether to inspect calendar tools, reminder tools, mail tools, GitHub tools, local dashboards, RSS feeds, or the web.

With AgentFeeds, the agent first checks the local stream brief/search/read path, then answers from already-refreshed context with source names and freshness. If a stream is missing, stale, or failing, the agent can say so and refresh or reconfigure only when needed.

## Quick Demo

![AgentFeeds interactive session demo](assets/agentfeeds-demo.gif)

A healthy session-start brief looks like this:

```xml
<agentfeeds>
Fresh local context. Health: ok.
Prefer relevant streams before web/API calls or asking again.
- calendar: work-calendar
- mac: reminders-pending, mail-unread
- dev: github-notifications, project-git-status
- news: openai-com, anthropic-com
</agentfeeds>
```

The brief is intentionally compact. It tells the agent what fresh local context exists, then the agent reads only relevant streams with `search` or `streams read`.

## Install The Skill

Download the latest skill bundle from the bundle release and unpack it into your agent's skills directory:

```text
https://github.com/verkyyi/agentfeeds/releases/tag/skill-v0.1.2
```

The release asset is:

```text
agentfeeds-skill-v0.1.2.zip
```

Release notes are tracked in [CHANGELOG.md](CHANGELOG.md) and on the [skill-v0.1.2 GitHub release](https://github.com/verkyyi/agentfeeds/releases/tag/skill-v0.1.2).

The unpacked skill folder contains:

- `SKILL.md`: agent-facing instructions
- `agents/openai.yaml`: skill list metadata for compatible UIs
- `scripts/`: deterministic CLI entry points the agent can run
- `scripts/lib/agentfeeds_runtime/`: bundled Python runtime package
- `catalog/`: frozen built-in template catalog fallback
- `references/`: setup, template authoring, background refresh, and publishing notes loaded only when needed
- `assets/`: demo and skill assets

### For Agent Hosts And Debugging

From the skill root, run setup once:

```bash
python3 scripts/setup.py
```

This installs the bundled runtime into `~/.agentfeeds/runtime-venv/`. The script entry points automatically re-exec through that environment after setup:

```bash
python3 scripts/agentfeeds.py --help
python3 scripts/agentfeeds_fetch.py --help
```

Background refresh is required for normal ambient use:

```bash
python3 scripts/agentfeeds.py admin polling status
python3 scripts/agentfeeds.py admin polling install
python3 scripts/agentfeeds.py streams health
```

Agents should also generate the compact session brief and place it into the most stable prompt/context slot their host provides, preferably a system-level slot:

```bash
python3 scripts/agentfeeds.py brief
```

The default brief is intentionally compact and stable for prompt caching. It lists active stream IDs and titles without volatile timestamps.

## What The Skill Enables

AgentFeeds gives the agent a small local control surface:

- `python3 scripts/agentfeeds.py templates find/show ...` discovers reusable feed definitions
- `python3 scripts/agentfeeds.py subscribe ...` creates active subscriptions
- `python3 scripts/agentfeeds.py streams ...` lists, finds, and reads refreshed data
- `python3 scripts/agentfeeds.py search ...` searches refreshed local state and returns matching snippets
- `python3 scripts/agentfeeds.py streams health ...` reports missing, stale, and failing streams
- `python3 scripts/agentfeeds.py refresh ...` refreshes subscriptions
- `python3 scripts/agentfeeds.py admin polling ...` keeps subscriptions warm in the background
- `python3 scripts/agentfeeds.py brief` emits compact stable context for session-start prompt insertion

Runtime state lives under `~/.agentfeeds/`, but agents should normally use the CLI instead of reading or writing storage files directly. The file layout remains inspectable for debugging and local template authoring.

## Core Vocabulary

- Template: reusable feed definition. Some templates are ready to subscribe with no parameters; others require parameters.
- Subscription: configured active instance of a template.
- Stream: readable refreshed data for an active subscription.

For example, `news/rss-generic` is a template, `news/openai-com` can be a subscription, and the refreshed RSS items are the stream data.

## Operator Workflows

Ask your agent for outcomes in natural language:

```text
What AgentFeeds templates can I subscribe to?
```

```text
Subscribe me to OpenAI News from https://openai.com/news/rss.xml.
```

```text
Refresh OpenAI News and tell me what changed.
```

```text
Can AgentFeeds subscribe to my SQLite task database? If not, draft a template.
```

The skill instructs the agent to:

- search existing templates first
- collect only required template parameters
- subscribe through the CLI
- refresh before summarizing when freshness matters
- search local stream state before rerunning external searches or source-specific queries
- read compact stream data only when relevant
- draft and test local templates when no built-in template fits

For `local_command` templates, the agent should only create commands you explicitly approve. Command templates run without a shell, with timeout and output limits, and they will not execute until you approve the exact template and command digest with `admin templates approve-command` in an interactive terminal.

## Built-In Templates

Built-in template definitions live in the standalone catalog repository:

```text
https://github.com/verkyyi/agentfeeds-catalog
```

Release bundles include a frozen catalog snapshot so first-run template discovery works without reaching GitHub. Updating the catalog can still pull from the standalone catalog repo or an alternate source.

Current built-in templates include:

- `local/file`: read-only snapshot of one local text, Markdown, or JSON file
- `news/rss-generic`: RSS or Atom feed
- `dev/github-releases`: GitHub repository releases
- `dev/github-issues`: GitHub repository issues
- `dev/github-prs`: GitHub repository pull requests
- `mac/calendar-today`: today's local Calendar.app agenda
- `mac/reminders-pending`: pending Reminders.app items
- `mac/mail-unread`: unread Mail.app messages
- `mac/notes-recent`: recently modified Notes.app notes
- `calendar/ics`: public iCalendar feed
- `weather/openmeteo-current`: current weather by latitude/longitude
- `weather/openmeteo-forecast`: 7-day forecast by latitude/longitude
- `finance/exchangerate`: current exchange rates

Catalog loading can be pointed at a local checkout or alternate raw source:

```bash
AGENTFEEDS_CATALOG_DIR=~/projects/agentfeeds-catalog python3 scripts/agentfeeds_fetch.py --update-catalog
AGENTFEEDS_CATALOG_BASE_URL=https://raw.githubusercontent.com/verkyyi/agentfeeds-catalog/main python3 scripts/agentfeeds_fetch.py --update-catalog
```

## Background Refresh

Install background polling so subscriptions stay warm without waiting for the agent to refresh them during a conversation:

```bash
python3 scripts/agentfeeds.py admin polling install
```

Check it with:

```bash
python3 scripts/agentfeeds.py admin polling status
python3 scripts/agentfeeds.py streams health
```

Uninstall it only when you no longer want ambient refresh:

```bash
python3 scripts/agentfeeds.py admin polling uninstall
```

On macOS this installs a LaunchAgent at `~/Library/LaunchAgents/dev.agentfeeds.fetch.plist`. On Linux it installs a tagged crontab block. The interval is the shortest configured subscription interval, floored at 5 minutes.

## Host-Specific Bundles

The canonical skill bundle works in any compatible agent that can load `SKILL.md` and run the bundled scripts. Host-specific bundles add only install ergonomics and host glue, such as session-start hooks or prompt-slot wiring.

Hermes users can install the standalone Hermes plugin:

```bash
git clone https://github.com/verkyyi/agentfeeds-hermes-plugin ~/.hermes/plugins-src/agentfeeds-hermes-plugin
~/.hermes/plugins-src/agentfeeds-hermes-plugin/install.sh
```

The Hermes plugin vendors or links this canonical skill unmodified, installs command wrappers, enables the plugin, initializes `~/.agentfeeds/`, and wires compact stream metadata into Hermes turns.

Restart Hermes after installation.

## Publishing

This repo is the source tree for the skill. Release artifacts should be built as portable skill bundles:

```bash
python3 scripts/bundle/build_skill_bundle.py --output dist/agentfeeds-skill-v0.1.2.zip
```

The bundle intentionally includes only the skill surface, frozen catalog snapshot, and runtime files needed by agents. Repo-only docs, tests, build outputs, and caches are excluded.

## Distribution Model

AgentFeeds ships as one canonical skill with optional host-specific shells around it.

- The canonical skill bundle is the source of truth: `SKILL.md`, `agents/`, `references/`, `scripts/`, `assets/`, `catalog/`, `LICENSE`, and `pyproject.toml`.
- Host-specific bundles may vendor the canonical skill unmodified and add only host glue: manifests, hooks, installers, command wrappers, prompt-slot wiring, or one-click package formats.
- Runtime setup is shared under `~/.agentfeeds/runtime-venv/`; whichever bundle installs first creates it, and later bundles reuse it.

If a behavior is useful in every agent, keep it in this repo's `SKILL.md` or references. If it is meaningful only for one host, keep it in that host's adapter bundle. Do not fork `SKILL.md` per host; fix the canonical skill abstraction instead.

## FAQ

### Why not just use agent memory?

Memory is for durable facts that should survive across sessions. AgentFeeds is for fresh state that changes over time: feed items, repo issues, calendars, weather, dashboards, project notes, or command snapshots. The state is timestamped and refreshable instead of being mixed into chat history.

### Why not put everything in the prompt?

Large prompts are expensive, noisy, and stale. AgentFeeds lets the agent discover available streams, then read detailed state only when the user asks something relevant.

### Why not a vector database?

AgentFeeds is not semantic recall. It is structured, inspectable current state. Subscriptions, template definitions, schemas, and JSON state are plain files under `~/.agentfeeds/` so operators can debug what the agent sees.

### Why not MCP?

MCP is a tool interface. AgentFeeds is a local state substrate: background refresh, subscriptions, a compact catalog, and state files that agents can inspect across sessions. They can complement each other.

### Is this an RSS reader?

RSS is one template type. AgentFeeds also supports local files, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, and operator-approved local commands. The product is the subscription/state layer for agents, not a human feed UI.

## More Docs

See [CHANGELOG.md](CHANGELOG.md) for release history.

See [docs/DEMO.md](docs/DEMO.md) for the demo transcript and talking points.

See [docs/SHARING.md](docs/SHARING.md) for a short pitch, demo script, and release notes draft.

For product framing, use cases, and benefits, see [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

For protocol and implementation details, see [docs/SPEC.md](docs/SPEC.md).
