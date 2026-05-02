# Agent Feeds Product Spec

## Summary

Agent Feeds is a local-first ambient context layer for Hermes and personal agents.

If Agent Skills teach an agent how to act, Agent Feeds help the agent stay aware of what is currently happening around it. It gives Hermes a compact map of subscribed local streams, while detailed state stays in inspectable JSON files on disk.

The product goal is simple: make a new or ongoing Hermes session useful faster, with less repeated setup, fewer tokens spent carrying bulky context, and less need to search or refetch information that is already available locally.

## Problem

Personal agents are becoming more useful, but they still begin many conversations with little awareness of the user's current local state.

Common examples:

- What projects is the user tracking?
- What local notes should the agent know about?
- What GitHub repos, issues, PRs, and releases matter to the user?
- What calendar feeds, RSS feeds, or dashboards should be fresh?
- What local command can summarize a private tool, database, or workspace?

Without a local ambient layer, users and agents fall into repetitive patterns:

- The user re-explains the same context across conversations.
- The agent re-runs commands or searches the web for information that could already be cached.
- Large private context gets pasted into prompts.
- New Hermes sessions need manual onboarding before they become useful.
- Freshness is unclear because context is mixed into chat history instead of backed by timestamped state.

Agent Feeds exists to move this recurring context into a small local substrate that Hermes can inspect when needed.

## Non-Goals

Agent Feeds is not intended to be:

- a general memory system
- a vector database
- a full ETL platform
- a hosted sync service
- a replacement for Hermes skills
- a replacement for web search when local state does not cover the question

It is a refreshable local state layer for current context.

## Target Users

Primary users:

- Hermes operators who use Hermes as a personal agent.
- Users who want their agent to stay aware of local/private state.
- Builders creating custom provider adapters for their own workflows.

Secondary users:

- OpenClaw or other personal-agent users exploring local context patterns.
- Developers building agent memory, context, or awareness infrastructure.

## Product Principles

### Local First

The user's active subscriptions and state live under `~/.agentfeeds`. Detailed data does not need to leave the machine.

### Compact By Default

Hermes should not carry every subscribed data source in every prompt. The injected context should only include a compact list of available streams. The agent reads the detailed state file only when relevant.

### Agent-Orchestrated

The expected UX is conversational. Users should be able to ask Hermes to subscribe, refresh, inspect, or draft providers without knowing CLI flags.

### Inspectable

Everything important is plain files: subscription YAML, catalog Markdown, provider YAML, JSON schemas, and JSON state.

### Fast To Re-Onboard

A new Hermes session should quickly learn what local streams exist by reading compact metadata, then answer from already-refreshed state when possible.

### Extensible By Operators

Operators should be able to add private/local sources without waiting for upstream support. Hermes can draft provider YAML and test it before installing it into live subscriptions.

## Core Concepts

### Provider

A provider is a reusable stream template. It defines where data comes from and how to fetch it.

Examples:

- `news/rss-generic`
- `dev/github-issues`
- `calendar/ics`
- `local/file`

### Subscription

A subscription is a concrete active instance of a provider.

Examples:

- `news/openai-com`
- `dev/nousresearch-hermes-agent-issues`
- `local/project-notes-md`

Templates are for discovery. Subscriptions are active context.

### State File

A state file is the detailed JSON payload that Hermes reads when the user asks a related question.

State files are timestamped, structured, and stored under `~/.agentfeeds/state`.

### Catalog

`~/.agentfeeds/catalog.md` is the compact active-stream map. Hermes uses it to locate state files without loading all data into the prompt.

### Adapter

An adapter is the fetch mechanism behind a provider. Current adapter types include HTTP JSON, RSS, iCalendar, local files, and local commands.

## Primary Use Cases

### 1. Fast Answers From Local State

User asks:

```text
What is on Hacker News right now?
```

Hermes checks the Agent Feeds catalog, sees a fresh Hacker News subscription, reads the local state file, and answers without web search.

Benefit:

- quicker response
- fewer network calls
- clearer data source

### 2. Private Project Context

User asks:

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

Hermes subscribes through the local file provider. Future sessions can see that "Project notes" exists and read the state file when relevant.

Benefit:

- less repeated explanation
- private context stays local
- new sessions onboard faster

### 3. GitHub Ambient Awareness

User asks:

```text
Subscribe to open issues and PRs for NousResearch/hermes-agent.
```

Hermes creates concrete subscriptions for GitHub issues and PRs. Background refresh keeps them warm.

Benefit:

- the agent can answer repo-status questions quickly
- issue/PR history is event-shaped and deduplicated
- the user does not need to repeat owner/repo/state parameters

### 4. Calendar And Public Feed Awareness

User subscribes to an ICS calendar or RSS feed.

Hermes can later answer:

```text
What is coming up on this calendar?
What changed in the feed?
```

Benefit:

- useful current context without every turn carrying feed contents
- consistent state shape across different sources

### 5. Custom Local Command Providers

User asks:

```text
Can Agent Feeds subscribe to my local task database?
```

If no provider exists, Hermes can draft a `local_command` provider that runs an operator-approved read-only command. The command can output one snapshot or a JSON list of events.

Benefit:

- private tools become agent-readable without building a full API
- commands are explicit argv arrays, not shell strings
- provider testing can happen before live subscription

### 6. New Hermes Session Onboarding

A new Hermes conversation starts.

The plugin injects compact metadata:

```text
Available local streams:
- local/project-notes-md: Project notes
- dev/hackernews-frontpage: Hacker News front page
```

Hermes now knows what local context exists without loading every state file.

Benefit:

- faster session start
- fewer tokens
- less context drift

## User Experience

The preferred interface is natural language through Hermes:

```text
What Agent Feeds providers can I subscribe to?
Subscribe me to Hacker News front page.
Subscribe my project notes at ~/notes/project.md as Project notes.
Refresh Project notes and summarize it.
Can Agent Feeds subscribe to my SQLite task database? If not, draft a provider.
```

The CLI exists for inspection, debugging, and agent orchestration:

```bash
agentfeeds discover local
agentfeeds subscribe local/file path=~/notes/project.md --title "Project notes"
agentfeeds status
agentfeeds providers test personal/tasks --json
```

Users should not need to memorize these commands for normal operation.

## Benefits

### Faster Responses

Fresh local state can answer many questions immediately.

### Token Savings

Only compact stream metadata is injected. Large data stays on disk until relevant.

### Easier Hermes Onboarding

Subscriptions and state survive across sessions. A new conversation can discover existing streams quickly.

### Better Freshness Semantics

Each state file has update and staleness metadata. The agent can tell whether local data is fresh enough.

### Local And Private By Design

Local notes, files, and command outputs stay in the user's `~/.agentfeeds` directory.

### Operator Extensibility

Users can add custom providers for private tools, local files, dashboards, or command outputs.

### Debuggability

Every layer is readable:

- `subscriptions.yaml`
- `catalog.md`
- provider YAML
- JSON schemas
- JSON state files

## Why Not Just Use Agent Skills?

Agent Skills are procedural. They teach Hermes how to do things.

Agent Feeds are ambient. They tell Hermes what local streams exist and where to read their current state.

They are complementary:

- Skills: "How do I subscribe, refresh, or author a provider?"
- Feeds: "What subscribed context is available right now?"

Together they let Hermes both act and stay aware.

## Why Not Put Everything In The Prompt?

Putting all state in the prompt creates three problems:

- It spends tokens every turn, even when the data is irrelevant.
- It risks exposing private data more broadly than needed.
- It makes freshness hard to reason about.

Agent Feeds keeps only a compact map in context and leaves detailed data in local state files.

## Why Not Just Web Search?

Web search is useful when the local state does not cover the question. But for subscribed sources, local state is often better:

- it is faster
- it can include private/local data
- it has known freshness metadata
- it avoids repeated network work
- it gives the user an inspectable record of what the agent used

## Success Metrics

Agent Feeds is working if:

- Hermes can answer subscribed-context questions without the user re-explaining setup.
- New sessions quickly discover existing local streams.
- Users see faster answers for refreshed streams.
- Users spend fewer tokens carrying bulky context.
- Operators can add custom providers without editing core code.
- State files are easy to inspect and trust.

## Current Product Surface

Available today:

- Hermes plugin and skill bundle
- local subscription root at `~/.agentfeeds`
- compact catalog injection
- state files as JSON
- background fetcher
- built-in providers for local files, RSS, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, USGS earthquakes, and ISS location
- local provider authoring
- local command adapter for snapshots and JSON-derived event streams
- provider dry-run testing

## Future Directions

High-value next steps:

- more personal/private built-in providers
- first-class examples for common Hermes operator workflows
- stronger local-command safety metadata
- richer provider authoring recipes
- provider packs for specific personal-agent setups
- visual or textual demos showing before/after token and response-time improvements

