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
- Builders creating custom feed templates for their own workflows.

Secondary users:

- OpenClaw or other personal-agent users exploring local context patterns.
- Developers building agent memory, context, or awareness infrastructure.

## Product Principles

### Local First

The user's active subscriptions and state live under `~/.agentfeeds`. Detailed data does not need to leave the machine.

### Compact By Default

Hermes should not carry every subscribed data source in every prompt. The injected context should come from `python3 scripts/agentfeeds.py brief`: a compact, stable list of available streams designed for system-level prompt/context slots and prompt caching. The agent reads detailed stream data through the CLI only when relevant.

### Agent-Orchestrated

The expected UX is conversational. Users should be able to ask Hermes to subscribe, refresh, inspect, or draft templates without knowing CLI flags.

### Inspectable

Everything important is plain files: subscription YAML, catalog Markdown, template YAML, JSON schemas, and JSON state.

### Fast To Re-Onboard

A new Hermes session should quickly learn what local streams exist by reading compact metadata, then answer from already-refreshed state when possible.

### Warm By Default

Background refresh is expected for normal use. The agent should try to verify or install polling at session start, and should report degraded ambient awareness when the host scheduler is unavailable.

### Extensible By Operators

Operators should be able to add private/local sources without waiting for upstream support. Hermes can draft template YAML and test it before installing it into live subscriptions.

## Core Concepts

### Template

A template is a reusable feed definition. It defines where data comes from and how to fetch it. Some templates are ready to subscribe as-is; others require parameters.

Examples:

- `news/rss-generic`
- `dev/github-issues`
- `calendar/ics`
- `local/file`

### Subscription

A subscription is a concrete active instance of a template.

Examples:

- `news/openai-com`
- `dev/nousresearch-hermes-agent-issues`
- `local/project-notes-md`

Templates are for discovery. Subscriptions are active context.

### Stream Data

Stream data is the detailed JSON payload that Hermes reads when the user asks a related question.

Agents should read it through `python3 scripts/agentfeeds.py streams read <subscription-id> --json`. The underlying state files remain timestamped, structured, and inspectable on disk for debugging.

### Active Stream Map

`python3 scripts/agentfeeds.py streams list` and `python3 scripts/agentfeeds.py streams search` provide the compact active-stream map. Hermes uses that map to locate relevant subscribed context without loading all data into the prompt.

`python3 scripts/agentfeeds.py brief` provides the stable session-start prompt surface. By default it avoids timestamps and volatile freshness fields so repeated sessions can benefit from model-side prompt caching.

### Adapter

An adapter is the fetch mechanism behind a template. Current adapter types include HTTP JSON, RSS, iCalendar, local files, and local commands.

## Primary Use Cases

### 1. Fast Answers From Local State

User asks:

```text
What is on Hacker News right now?
```

Hermes checks active Agent Feeds streams, sees a fresh Hacker News subscription, reads the stream through the CLI, and answers without web search.

Benefit:

- quicker response
- fewer network calls
- clearer data source

### 2. Private Project Context

User asks:

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

Hermes subscribes through the local file template. Future sessions can see that "Project notes" exists and read the stream through the CLI when relevant.

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

Hermes can later answer one prompt at a time:

```text
What is coming up on this calendar?
```

```text
What changed in the feed?
```

Benefit:

- useful current context without every turn carrying feed contents
- consistent state shape across different sources

### 5. Custom Local Command Templates

User asks:

```text
Can Agent Feeds subscribe to my local task database?
```

If no template exists, Hermes can draft a `local_command` template that runs an operator-approved read-only command. The command can output one snapshot or a JSON list of events.

Benefit:

- private tools become agent-readable without building a full API
- commands are explicit argv arrays, not shell strings
- template testing can happen before live subscription

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

The preferred interface is natural language through Hermes. Each example is meant to be used as a single message:

```text
What Agent Feeds templates can I subscribe to?
```

```text
Subscribe me to Hacker News front page.
```

```text
Subscribe my project notes at ~/notes/project.md as Project notes.
```

```text
Refresh Project notes and summarize it.
```

```text
Can Agent Feeds subscribe to my SQLite task database? If not, draft a template.
```

The CLI exists for inspection, debugging, and agent orchestration:

```bash
python3 scripts/agentfeeds.py templates search local
python3 scripts/agentfeeds.py subscribe local/file path=~/notes/project.md --title "Project notes"
python3 scripts/agentfeeds.py streams list
python3 scripts/agentfeeds.py templates test personal/tasks --json
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

Users can add custom templates for private tools, local files, dashboards, or command outputs.

### Debuggability

Every layer is readable for debugging:

- active subscription YAML
- compact catalog fallback
- template YAML
- JSON schemas
- JSON state files

## Why Not Just Use Agent Skills?

Agent Skills are procedural. They teach Hermes how to do things.

Agent Feeds are ambient. They tell Hermes what local streams exist and where to read their current state.

They are complementary:

- Skills: "How do I subscribe, refresh, or author a template?"
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
- Operators can add custom templates without editing core code.
- State files are easy to inspect and trust.

## Current Product Surface

Available today:

- standalone Hermes plugin and skill bundle
- standalone built-in template catalog
- local subscription root at `~/.agentfeeds`
- compact catalog injection
- state files as JSON
- background fetcher
- built-in templates for local files, RSS, Hacker News, GitHub releases/issues/PRs, ICS calendars, weather, exchange rates, USGS earthquakes, and ISS location
- local template authoring
- local command adapter for snapshots and JSON-derived event streams
- template dry-run testing

## Future Directions

High-value next steps:

- more personal/private built-in templates
- first-class examples for common Hermes operator workflows
- stronger local-command safety metadata
- richer template authoring recipes
- template packs for specific personal-agent setups
- visual or textual demos showing before/after token and response-time improvements
