---
name: agentfeeds
description: Use Agent Feeds for ambient awareness from continuously refreshed local streams under ~/.agentfeeds. Use at session start to set up background refresh and compact stream brief context, and when answering prompts that may be covered by changing local context such as feeds, subscriptions, templates, subscribed stream state, RSS/news/GitHub/calendar/weather, personal sources, or fresh local context before web search or recomputing source data.
---

# Agent Feeds

Agent Feeds is a local-first ambient context layer for agents. A background fetcher keeps changing stream state warm on disk so agents can answer from local, inspectable context before re-searching, querying, processing, or asking the user to repeat information.

Use this skill at session start and when the user asks to discover templates, subscribe to a feed/source, inspect Agent Feeds state, answer from subscribed streams, or draft/test a local template. Also use it before web search or expensive source-specific queries when a subscribed stream may already cover the prompt.

Requires shell access, Python 3.11+, and either `pip` or `uv` for runtime setup. Network access is needed for setup, remote catalog updates, and public feed templates.

## Runtime Model

Agent Feeds is a portable Agent Skill with bundled Python scripts. Use the scripts from the skill root:

```bash
python3 scripts/agentfeeds.py        # management CLI: templates, subscribe, streams, template authoring
python3 scripts/agentfeeds_fetch.py  # worker CLI: refresh subscriptions, update catalog cache, write state
```

Runtime state defaults to `~/.agentfeeds/`, but agents should treat the file layout as an implementation detail. Prefer `python3 scripts/agentfeeds.py` for discovery, subscription inspection, state reads, and local template paths. Only inspect files directly when debugging, authoring a local template after scaffolding, or when the CLI is unavailable.

Background refresh is required for normal use. The agent should try to keep it installed and should report clearly if the host cannot support the scheduler.

## Setup

Before doing real work from a fresh checkout, install the Python runtime into a local virtual environment:

```bash
python3 scripts/setup.py
```

The setup script installs an editable runtime into `~/.agentfeeds/runtime-venv/`. The script entry points automatically re-exec through that venv when it exists, so subsequent examples can use `python3 scripts/...` directly.

Check availability:

```bash
python3 scripts/agentfeeds.py --help
python3 scripts/agentfeeds_fetch.py --help
```

Ensure background refresh is installed:

```bash
python3 scripts/agentfeeds.py polling status --json
python3 scripts/agentfeeds.py polling install
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

At the start of each session:

1. Ensure runtime setup has been completed. If the bundled scripts fail because dependencies are missing, run `python3 scripts/setup.py`.
2. Ensure background refresh is installed with `python3 scripts/agentfeeds.py polling status --json`; if it is missing, run `python3 scripts/agentfeeds.py polling install`.
3. Generate stable compact context with `python3 scripts/agentfeeds.py brief`.
4. If the agent framework supports prompt slots, place the exact brief output in the system-level or persistent context slot so stable stream metadata can benefit from model-side prompt caching.

The default brief intentionally avoids volatile timestamps. Use `python3 scripts/agentfeeds.py brief --include-freshness` only when the user asks about freshness or debugging.

Use `python3 scripts/agentfeeds.py search <topic> --json` to find relevant local state snippets during a task. Use `python3 scripts/agentfeeds.py streams list` or `python3 scripts/agentfeeds.py streams search <topic>` only when you need stream metadata. Do not read raw state files during normal operation.

## Discover Templates

When the user asks what Agent Feeds can subscribe to:

```bash
python3 scripts/agentfeeds.py templates search <query>
python3 scripts/agentfeeds.py templates show <template-id>
```

If the catalog cache is missing or stale, run:

```bash
python3 scripts/agentfeeds_fetch.py --update-catalog --regenerate-catalog
```

Then retry discovery.

## Subscribe

When the user asks to subscribe to a source:

1. Identify the template with `python3 scripts/agentfeeds.py templates search <query>`.
2. Collect required parameters from the template match.
3. Subscribe with the management CLI.

Examples:

```bash
python3 scripts/agentfeeds.py subscribe dev/hackernews-frontpage
python3 scripts/agentfeeds.py subscribe news/rss-generic url=https://example.com/rss.xml --title "Example RSS"
python3 scripts/agentfeeds.py subscribe local/file path=~/notes/project.md --title "Project notes"
```

After subscribing, read or refresh the resulting state before summarizing what changed:

```bash
python3 scripts/agentfeeds.py streams list
```

## Answer From Local State

When the user asks about a topic covered by a subscribed stream:

1. Search existing local state with `python3 scripts/agentfeeds.py search <topic> --json`.
2. If needed, inspect metadata with `python3 scripts/agentfeeds.py streams show <subscription-id> --json`.
3. If stale and freshness matters, refresh the stream before answering.
4. Read compact data with `python3 scripts/agentfeeds.py streams read <subscription-id> --limit 20 --json`.

Refresh one subscription:

```bash
python3 scripts/agentfeeds_fetch.py --stream <subscription-id>
```

Refresh all subscriptions only when the user asks for a full refresh:

```bash
python3 scripts/agentfeeds_fetch.py --all
```

If non-stale stream data covers the question, answer from it and avoid web search unless the user explicitly asks for outside/current web information beyond the subscribed data.

## Unsubscribe

When the user asks to remove a subscription:

```bash
python3 scripts/agentfeeds.py streams list
python3 scripts/agentfeeds.py unsubscribe <subscription-id>
```

If the user names a template instead of a concrete subscription, list matching active streams and ask which one to remove.

## Local Template Authoring

When no built-in template fits:

1. Run `python3 scripts/agentfeeds.py templates adapters`.
2. Draft a local template with `python3 scripts/agentfeeds.py templates scaffold <adapter-kind> <template-id>`.
3. Edit the generated template YAML at the path reported by the scaffold command or under `python3 scripts/agentfeeds.py templates path`.
4. Validate and test before subscribing.

Commands:

```bash
python3 scripts/agentfeeds.py templates path
python3 scripts/agentfeeds.py templates scaffold local_file personal/notes
python3 scripts/agentfeeds.py templates validate
python3 scripts/agentfeeds.py templates test <template-id> key=value
```

For `local_command` templates, use argv arrays only. Only create command templates for explicitly requested or approved read-only commands. Avoid commands that mutate files, cloud resources, accounts, or external services.

For adapter-specific details, read `references/template-authoring.md`.

## Safety Rules

- Use `python3 scripts/agentfeeds.py subscribe` and `python3 scripts/agentfeeds.py unsubscribe` for subscription changes.
- Use `python3 scripts/agentfeeds_fetch.py` or `python3 scripts/agentfeeds.py refresh` for refreshes.
- Do not hand-write state files.
- Do not include secrets in template YAML.
- Prefer local/private templates for personal-agent context before suggesting public feeds.
