# Sharing Agent Feeds

Use this when introducing Agent Feeds to personal-agent builders, Hermes operators, or people working on local context systems.

## Short Pitch

Agent Feeds is a local-first ambient context layer for personal agents like Hermes.

It lets an agent subscribe to local or public streams, keep JSON state files fresh in the background, and inject only compact stream metadata into sessions. When relevant, the agent reads local state before using web search.

Agent Feeds is not memory. It is a refreshable, inspectable file layer for current context.

## Longer Pitch

I have been building Agent Feeds, a local-first subscription layer for personal agents.

The idea is simple: personal agents need fresh awareness of local and private state, but that state should not be dumped into every prompt. Agent Feeds keeps detailed data on disk under `~/.agentfeeds/state/`, injects only compact stream metadata into Hermes, and lets the agent read the right state file only when it is relevant.

Current providers include local files, RSS/Atom, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, and argv-only local commands. Local commands can produce either a current snapshot or JSON-derived events.

Repo: https://github.com/verkyyi/agentfeeds

Product spec: https://github.com/verkyyi/agentfeeds/blob/main/docs/PRODUCT_SPEC.md

## Demo Script

```bash
git clone https://github.com/verkyyi/agentfeeds
cd agentfeeds
./integrations/hermes/agentfeeds/install.sh
```

Then ask Hermes:

```text
What Agent Feeds providers can I subscribe to?
Subscribe me to Hacker News front page.
Show me the current Hacker News front page from Agent Feeds.
Subscribe my project notes at ~/notes/project.md as Project notes.
Refresh Project notes and summarize it.
```

Direct CLI inspection:

```bash
agentfeeds discover hacker
agentfeeds subscribe dev/hackernews-frontpage
agentfeeds status
cat ~/.agentfeeds/catalog.md
```

Provider authoring smoke test:

```bash
agentfeeds providers adapters
agentfeeds providers scaffold local_command personal/status
agentfeeds providers validate
agentfeeds providers test personal/status --json
```

## Release Notes Draft

Title:

```text
Agent Feeds v0.1.0: Local ambient context for personal agents
```

Body:

```text
Agent Feeds is a local-first ambient context layer for personal agents.

This first release focuses on personal agents, with a Hermes integration included:
- Hermes plugin and skill bundle
- local subscriptions under ~/.agentfeeds
- compact catalog injection
- background fetcher with launchd/cron installer
- built-in providers for local files, RSS, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, earthquakes, and ISS location
- local provider authoring tools
- argv-only local_command adapter for snapshots and JSON-derived event streams
- provider dry-run testing with agentfeeds providers test

The core design is intentionally file-based: detailed state stays in JSON files on disk, and the agent reads it only when relevant.

Agent Feeds is not long-term memory, a vector database, a hosted sync service, or an RSS reader UI. It is a small inspectable substrate for fresh agent context.
```

## Suggested Audiences

- Hermes and OpenClaw operators
- personal-agent builders
- local-first AI tooling communities
- people building agent context, memory, or awareness systems
- developers who want agents to read local state without always using web search
