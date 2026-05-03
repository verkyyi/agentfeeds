---
name: agentfeeds
description: Use Agent Feeds to discover, subscribe to, refresh, and answer from local ambient context streams stored under ~/.agentfeeds. Use when the user asks about feeds, subscriptions, provider catalogs, local state files, RSS/news/GitHub/calendar/weather context, or wants fresh local context before web search.
license: MIT
compatibility: Requires shell access, Python 3.11+, and either uv or installed Agent Feeds CLI entry points. Network access is needed for remote catalog updates and public providers.
metadata:
  author: verkyyi
  version: "0.1.0"
  repository: https://github.com/verkyyi/agentfeeds
---

# Agent Feeds

Agent Feeds is a local-first ambient context layer for agents. It keeps refreshable stream state on disk so agents can answer from local, inspectable context before re-searching or asking the user to repeat information.

Use this skill when the user asks to discover providers, subscribe to a feed/source, refresh feed data, inspect Agent Feeds state, answer from subscribed streams, or draft/test a local provider.

## Runtime Model

Agent Feeds uses two command-line entry points:

```bash
agentfeeds        # management CLI: discover, subscribe, status, providers
agentfeeds-fetch  # worker CLI: refresh subscriptions, update catalog cache, write state
```

Runtime files live under `~/.agentfeeds/`:

- `subscriptions.yaml` is the source of truth for active subscriptions.
- `catalog-cache/` contains cached built-in provider definitions from `agentfeeds-catalog`.
- `catalog.md` summarizes active subscriptions for agent use.
- `state/` contains JSON state files written by `agentfeeds-fetch`.
- `providers/` contains user-local provider YAML and schemas.

Treat `~/.agentfeeds/state/` as fetcher-owned. Never hand-edit state files.

## Command Availability

First check whether commands are installed:

```bash
agentfeeds --help
agentfeeds-fetch --help
```

If commands are not on `PATH` and this skill is being used from a full checkout of the `agentfeeds` repo, run commands through the repo project:

```bash
uv run --project <agentfeeds-skill-root> agentfeeds --help
uv run --project <agentfeeds-skill-root> agentfeeds-fetch --help
```

Use the direct command names in examples below. If needed, replace them with the `uv run --project ...` form.

## Session Start

If `~/.agentfeeds/catalog.md` exists, read it before answering questions that may be covered by local streams. It points to the concrete state files to inspect.

If `catalog.md` does not exist, continue normally. The user may not have subscribed to streams yet.

## Discover Providers

When the user asks what Agent Feeds can subscribe to:

```bash
agentfeeds discover <query>
```

If the catalog cache is missing or stale, run:

```bash
agentfeeds-fetch --update-catalog --regenerate-catalog
```

Then retry discovery.

## Subscribe

When the user asks to subscribe to a source:

1. Identify the provider with `agentfeeds discover <query>`.
2. Collect required parameters from the provider match.
3. Subscribe with the management CLI.

Examples:

```bash
agentfeeds subscribe dev/hackernews-frontpage
agentfeeds subscribe news/rss-generic url=https://example.com/rss.xml --title "Example RSS"
agentfeeds subscribe local/file path=~/notes/project.md --title "Project notes"
```

After subscribing, read or refresh the resulting state before summarizing what changed:

```bash
agentfeeds status
```

## Answer From Local State

When the user asks about a topic covered by a subscribed stream:

1. Read `~/.agentfeeds/catalog.md`.
2. Locate the matching state path under `~/.agentfeeds/state/`.
3. Read the JSON state file.
4. Check `_meta.stale`.
5. If stale and freshness matters, refresh the stream before answering.

Refresh one subscription:

```bash
agentfeeds-fetch --stream <subscription-id>
```

Refresh all subscriptions only when the user asks for a full refresh:

```bash
agentfeeds-fetch --all
```

If a non-stale state file covers the question, answer from it and avoid web search unless the user explicitly asks for outside/current web information beyond the subscribed data.

## Unsubscribe

When the user asks to remove a subscription:

```bash
agentfeeds list
agentfeeds unsubscribe <subscription-id>
```

If the user names a provider template instead of a concrete subscription, list matching active subscriptions and ask which one to remove.

## Local Provider Authoring

When no built-in provider fits:

1. Run `agentfeeds providers adapters`.
2. Draft a local provider with `agentfeeds providers scaffold <adapter-kind> <provider-id>`.
3. Edit the generated provider YAML under `~/.agentfeeds/providers/streams/`.
4. Validate and test before subscribing.

Commands:

```bash
agentfeeds providers path
agentfeeds providers scaffold local_file personal/notes
agentfeeds providers validate
agentfeeds providers test <provider-id> key=value
```

For `local_command` providers, use argv arrays only. Only create command providers for explicitly requested or approved read-only commands. Avoid commands that mutate files, cloud resources, accounts, or external services.

## Safety Rules

- Use `agentfeeds subscribe` and `agentfeeds unsubscribe` for subscription changes.
- Use `agentfeeds-fetch` or `agentfeeds refresh` for refreshes.
- Do not hand-write files in `~/.agentfeeds/state/`.
- Do not include secrets in provider YAML.
- Prefer local/private providers for personal-agent context before suggesting public feeds.
