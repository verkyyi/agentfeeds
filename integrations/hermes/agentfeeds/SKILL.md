---
name: agentfeeds
description: Use local Agent Feeds subscriptions and state files for ambient context. Use when subscribing to feeds, refreshing feeds, discovering available streams, or answering from ~/.agentfeeds state files.
---

# Agent Feeds

Use Agent Feeds to answer questions from local subscribed data streams before searching the web.

## Session Start

At the start of a session, check whether `~/.agentfeeds/catalog.md` exists.

If it exists, read it and treat its listed streams as available local context. Detailed data is in the state file shown for each stream.

If it does not exist, continue normally. The user may not have subscribed to any streams yet.

## Answering Questions

When the user asks about a topic covered by a subscribed stream:

1. Read the matching state file from `~/.agentfeeds/state/`.
2. Check `_meta.stale`.
3. If `_meta.stale` is `false`, answer from the state file and do not web-search.
4. If `_meta.stale` is `true`, refresh the stream before answering when freshness matters.

State files are read-only from the agent perspective. Never edit files under `~/.agentfeeds/state/` directly.

## Refreshing Stale Data

When a covered state file is stale and the user asks about current data, run:

```bash
agentfeeds-fetch --stream <subscription-id>
```

Then re-read the state file and answer from the refreshed data.

Use `agentfeeds-fetch --all` only when the user asks to refresh all subscriptions.

## Subscribing

When the user asks to subscribe to something, load `recipes/subscribe.md` and follow it.

Subscriptions are stored in `~/.agentfeeds/subscriptions.yaml`. Prefer the `agentfeeds` CLI for changes; the fetcher owns state-file writes.

Prefer the management CLI for subscription changes:

```bash
agentfeeds subscribe <provider-id> key=value
agentfeeds subscribe <provider-id> key=value --id <subscription-id> --title "<title>"
agentfeeds subscribe local/file path=/absolute/or/~/file.md --title "<title>"
agentfeeds unsubscribe <subscription-id>
agentfeeds discover <query>
agentfeeds status
```

## Unsubscribing

When the user asks to remove a subscription, load `recipes/unsubscribe.md` and follow it.

## Discovery

When the user asks what streams are available, load `recipes/discover.md` and search `~/.agentfeeds/catalog-cache/INDEX.json`.

If the local catalog cache is missing, run:

```bash
agentfeeds-fetch --update-catalog
```

Then retry discovery.

## File Rules

- Read `~/.agentfeeds/catalog.md` for the active subscription summary.
- Read state files listed in `catalog.md` for actual data.
- Change subscriptions with `agentfeeds subscribe` / `agentfeeds unsubscribe`.
- Never hand-write files in `~/.agentfeeds/state/`.
- Use `agentfeeds-fetch --regenerate-catalog` after subscription edits that do not fetch.

## Freshness Rule

If a non-stale state file covers the user's question, use it. Avoid web search unless the user explicitly asks for outside information or the local stream does not cover the question.
