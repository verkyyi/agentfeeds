---
name: agentfeeds
description: Use Agent Feeds to discover feed templates, subscribe to them, refresh streams, and answer from local ambient context stored under ~/.agentfeeds. Use when the user asks about feeds, subscriptions, templates, local state files, RSS/news/GitHub/calendar/weather context, or wants fresh local context before web search.
license: MIT
compatibility: Requires shell access, Python 3.11+, and either uv or installed Agent Feeds CLI entry points. Network access is needed for remote catalog updates and public feed templates.
metadata:
  author: verkyyi
  version: "0.1.0"
  repository: https://github.com/verkyyi/agentfeeds
---

# Agent Feeds

Agent Feeds is a local-first ambient context layer for agents. It keeps refreshable stream state on disk so agents can answer from local, inspectable context before re-searching or asking the user to repeat information.

Use this skill when the user asks to discover templates, subscribe to a feed/source, refresh feed data, inspect Agent Feeds state, answer from subscribed streams, or draft/test a local template.

## Runtime Model

Agent Feeds uses two command-line entry points:

```bash
agentfeeds        # management CLI: templates, subscribe, streams, template authoring
agentfeeds-fetch  # worker CLI: refresh subscriptions, update catalog cache, write state
```

Runtime state defaults to `~/.agentfeeds/`, but agents should treat the file layout as an implementation detail. Prefer the `agentfeeds` CLI for discovery, subscription inspection, state reads, and local template paths. Only inspect files directly when debugging, authoring a local template after `agentfeeds templates scaffold`, or when the CLI is unavailable.

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

Vocabulary:

- Template: reusable feed definition. Some templates are ready to subscribe with no parameters; others require parameters.
- Subscription: configured active instance of a template.
- Stream: readable refreshed data for an active subscription.

## Session Start

Use `agentfeeds streams list` or `agentfeeds streams search <topic>` to discover active local context. Do not read raw state files during normal operation.

## Discover Templates

When the user asks what Agent Feeds can subscribe to:

```bash
agentfeeds templates search <query>
agentfeeds templates show <template-id>
```

If the catalog cache is missing or stale, run:

```bash
agentfeeds-fetch --update-catalog --regenerate-catalog
```

Then retry discovery.

## Subscribe

When the user asks to subscribe to a source:

1. Identify the template with `agentfeeds templates search <query>`.
2. Collect required parameters from the template match.
3. Subscribe with the management CLI.

Examples:

```bash
agentfeeds subscribe dev/hackernews-frontpage
agentfeeds subscribe news/rss-generic url=https://example.com/rss.xml --title "Example RSS"
agentfeeds subscribe local/file path=~/notes/project.md --title "Project notes"
```

After subscribing, read or refresh the resulting state before summarizing what changed:

```bash
agentfeeds streams list
```

## Answer From Local State

When the user asks about a topic covered by a subscribed stream:

1. Find candidate active streams with `agentfeeds streams search <topic>`.
2. Inspect metadata with `agentfeeds streams show <subscription-id> --json`.
3. If stale and freshness matters, refresh the stream before answering.
4. Read compact data with `agentfeeds streams read <subscription-id> --limit 20 --json`.

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
agentfeeds streams list
agentfeeds unsubscribe <subscription-id>
```

If the user names a template instead of a concrete subscription, list matching active streams and ask which one to remove.

## Local Template Authoring

When no built-in template fits:

1. Run `agentfeeds templates adapters`.
2. Draft a local template with `agentfeeds templates scaffold <adapter-kind> <template-id>`.
3. Edit the generated template YAML at the path reported by the scaffold command or under `agentfeeds templates path`.
4. Validate and test before subscribing.

Commands:

```bash
agentfeeds templates path
agentfeeds templates scaffold local_file personal/notes
agentfeeds templates validate
agentfeeds templates test <template-id> key=value
```

For `local_command` templates, use argv arrays only. Only create command templates for explicitly requested or approved read-only commands. Avoid commands that mutate files, cloud resources, accounts, or external services.

## Safety Rules

- Use `agentfeeds subscribe` and `agentfeeds unsubscribe` for subscription changes.
- Use `agentfeeds-fetch` or `agentfeeds refresh` for refreshes.
- Do not hand-write state files.
- Do not include secrets in template YAML.
- Prefer local/private templates for personal-agent context before suggesting public feeds.
