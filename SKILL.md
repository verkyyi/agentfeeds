---
name: agentfeeds
description: Use Agent Feeds to discover feed templates, subscribe to them, refresh streams, and answer from local ambient context stored under ~/.agentfeeds. Use when the user asks about feeds, subscriptions, templates, subscribed stream state, RSS/news/GitHub/calendar/weather context, or wants fresh local context before web search.
---

# Agent Feeds

Agent Feeds is a local-first ambient context layer for agents. It keeps refreshable stream state on disk so agents can answer from local, inspectable context before re-searching or asking the user to repeat information.

Use this skill when the user asks to discover templates, subscribe to a feed/source, refresh feed data, inspect Agent Feeds state, answer from subscribed streams, or draft/test a local template.

Requires shell access, Python 3.11+, and either `pip` or `uv` for runtime setup. Network access is needed for setup, remote catalog updates, and public feed templates.

## Runtime Model

Agent Feeds is a portable Agent Skill with bundled Python scripts. Use the scripts from the skill root:

```bash
python scripts/agentfeeds.py        # management CLI: templates, subscribe, streams, template authoring
python scripts/agentfeeds_fetch.py  # worker CLI: refresh subscriptions, update catalog cache, write state
```

Runtime state defaults to `~/.agentfeeds/`, but agents should treat the file layout as an implementation detail. Prefer `python scripts/agentfeeds.py` for discovery, subscription inspection, state reads, and local template paths. Only inspect files directly when debugging, authoring a local template after scaffolding, or when the CLI is unavailable.

## Setup

Before doing real work from a fresh checkout, install the Python runtime into a local virtual environment:

```bash
python scripts/setup.py
```

The setup script installs an editable runtime into `~/.agentfeeds/runtime-venv/`. The script entry points automatically re-exec through that venv when it exists, so subsequent examples can use `python scripts/...` directly.

Check availability:

```bash
python scripts/agentfeeds.py --help
python scripts/agentfeeds_fetch.py --help
```

If console wrappers are already installed, `agentfeeds` and `agentfeeds-fetch` are acceptable equivalents, but prefer bundled scripts for portability.

Vocabulary:

- Template: reusable feed definition. Some templates are ready to subscribe with no parameters; others require parameters.
- Subscription: configured active instance of a template.
- Stream: readable refreshed data for an active subscription.

More detailed workflows are available only when needed:

- Runtime setup details: `references/runtime-setup.md`
- Template authoring details: `references/template-authoring.md`
- Background refresh details: `references/background-refresh.md`

## Session Start

Use `python scripts/agentfeeds.py streams list` or `python scripts/agentfeeds.py streams search <topic>` to discover active local context. Do not read raw state files during normal operation.

## Discover Templates

When the user asks what Agent Feeds can subscribe to:

```bash
python scripts/agentfeeds.py templates search <query>
python scripts/agentfeeds.py templates show <template-id>
```

If the catalog cache is missing or stale, run:

```bash
python scripts/agentfeeds_fetch.py --update-catalog --regenerate-catalog
```

Then retry discovery.

## Subscribe

When the user asks to subscribe to a source:

1. Identify the template with `python scripts/agentfeeds.py templates search <query>`.
2. Collect required parameters from the template match.
3. Subscribe with the management CLI.

Examples:

```bash
python scripts/agentfeeds.py subscribe dev/hackernews-frontpage
python scripts/agentfeeds.py subscribe news/rss-generic url=https://example.com/rss.xml --title "Example RSS"
python scripts/agentfeeds.py subscribe local/file path=~/notes/project.md --title "Project notes"
```

After subscribing, read or refresh the resulting state before summarizing what changed:

```bash
python scripts/agentfeeds.py streams list
```

## Answer From Local State

When the user asks about a topic covered by a subscribed stream:

1. Find candidate active streams with `python scripts/agentfeeds.py streams search <topic>`.
2. Inspect metadata with `python scripts/agentfeeds.py streams show <subscription-id> --json`.
3. If stale and freshness matters, refresh the stream before answering.
4. Read compact data with `python scripts/agentfeeds.py streams read <subscription-id> --limit 20 --json`.

Refresh one subscription:

```bash
python scripts/agentfeeds_fetch.py --stream <subscription-id>
```

Refresh all subscriptions only when the user asks for a full refresh:

```bash
python scripts/agentfeeds_fetch.py --all
```

If non-stale stream data covers the question, answer from it and avoid web search unless the user explicitly asks for outside/current web information beyond the subscribed data.

## Unsubscribe

When the user asks to remove a subscription:

```bash
python scripts/agentfeeds.py streams list
python scripts/agentfeeds.py unsubscribe <subscription-id>
```

If the user names a template instead of a concrete subscription, list matching active streams and ask which one to remove.

## Local Template Authoring

When no built-in template fits:

1. Run `python scripts/agentfeeds.py templates adapters`.
2. Draft a local template with `python scripts/agentfeeds.py templates scaffold <adapter-kind> <template-id>`.
3. Edit the generated template YAML at the path reported by the scaffold command or under `python scripts/agentfeeds.py templates path`.
4. Validate and test before subscribing.

Commands:

```bash
python scripts/agentfeeds.py templates path
python scripts/agentfeeds.py templates scaffold local_file personal/notes
python scripts/agentfeeds.py templates validate
python scripts/agentfeeds.py templates test <template-id> key=value
```

For `local_command` templates, use argv arrays only. Only create command templates for explicitly requested or approved read-only commands. Avoid commands that mutate files, cloud resources, accounts, or external services.

For adapter-specific details, read `references/template-authoring.md`.

## Safety Rules

- Use `python scripts/agentfeeds.py subscribe` and `python scripts/agentfeeds.py unsubscribe` for subscription changes.
- Use `python scripts/agentfeeds_fetch.py` or `python scripts/agentfeeds.py refresh` for refreshes.
- Do not hand-write state files.
- Do not include secrets in template YAML.
- Prefer local/private templates for personal-agent context before suggesting public feeds.
