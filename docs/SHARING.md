# Sharing Agent Feeds

Use this when introducing Agent Feeds to personal-agent builders, operators, or people working on local context systems.

## Short Pitch

Agent Feeds is a local-first ambient context layer for compatible personal agents.

It lets an agent subscribe to local or public streams, keep JSON stream state fresh in the background, and inspect only compact stream data when relevant before using web search.

Agent Feeds is not memory. It is a refreshable, inspectable file layer for current context.

## Longer Pitch

I have been building Agent Feeds, a local-first subscription layer for personal agents.

The idea is simple: personal agents need fresh awareness of local and private state, but that state should not be dumped into every prompt. Agent Feeds keeps detailed data on disk, exposes compact stream metadata, and lets the agent read relevant streams through the CLI only when needed.

Current templates include local files, RSS/Atom, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, and argv-only local commands. Some templates are ready to subscribe as-is; others take parameters. Local commands can produce either a current snapshot or JSON-derived events.

Repo: https://github.com/verkyyi/agentfeeds

Product spec: https://github.com/verkyyi/agentfeeds/blob/main/docs/PRODUCT_SPEC.md

## Demo Script

```bash
git clone https://github.com/verkyyi/agentfeeds-hermes-plugin ~/.hermes/plugins-src/agentfeeds-hermes-plugin
~/.hermes/plugins-src/agentfeeds-hermes-plugin/install.sh
```

Then ask your agent one prompt at a time:

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

Direct CLI inspection:

```bash
python3 scripts/agentfeeds.py templates search hacker
python3 scripts/agentfeeds.py subscribe dev/hackernews-frontpage
python3 scripts/agentfeeds.py streams list
python3 scripts/agentfeeds.py streams read dev/hackernews-frontpage --json
```

Template authoring smoke test:

```bash
python3 scripts/agentfeeds.py templates adapters
python3 scripts/agentfeeds.py templates scaffold local_command personal/status
python3 scripts/agentfeeds.py templates approve-command personal/status
python3 scripts/agentfeeds.py templates validate
python3 scripts/agentfeeds.py templates test personal/status --json
```

## Release Notes Draft

Title:

```text
Agent Feeds v0.1.0: Local ambient context for personal agents
```

Body:

```text
Agent Feeds is a local-first ambient context layer for personal agents.

This first release focuses on personal agents, with a standalone Hermes plugin available separately:
- Hermes plugin and skill bundle: https://github.com/verkyyi/agentfeeds-hermes-plugin
- built-in template catalog: https://github.com/verkyyi/agentfeeds-catalog
- local subscriptions under ~/.agentfeeds
- compact catalog injection
- background fetcher with launchd/cron installer
- built-in templates for local files, RSS, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, earthquakes, and ISS location
- local template authoring tools
- approved argv-only local_command adapter for snapshots and JSON-derived event streams
- template dry-run testing with python3 scripts/agentfeeds.py templates test

The core design is intentionally file-based: detailed state stays in JSON files on disk, and the agent reads it only when relevant.

Agent Feeds is not long-term memory, a vector database, a hosted sync service, or an RSS reader UI. It is a small inspectable substrate for fresh agent context.
```

## Suggested Audiences

- personal-agent operators
- personal-agent builders
- local-first AI tooling communities
- people building agent context, memory, or awareness systems
- developers who want agents to read local state without always using web search
