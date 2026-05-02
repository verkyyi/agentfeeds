# Agent Feeds Demo

This is the short launch demo for Agent Feeds v0.1.0.

## 60-second narrative

Personal agents often start sessions blind. Agent Feeds gives them a compact map of fresh local/public streams, while detailed state stays in inspectable JSON files on disk.

In the demo:

1. Discover a built-in provider.
2. Subscribe to Hacker News.
3. Subscribe a local project-notes file.
4. Inspect `~/.agentfeeds/catalog.md`.
5. Show that Hermes can answer from local state instead of web search.

![Agent Feeds terminal demo](assets/agentfeeds-demo.gif)

## Demo transcript

```console
$ agentfeeds discover hacker

dev/hackernews-frontpage: Hacker News front page [params: none, mode: event]

$ agentfeeds subscribe dev/hackernews-frontpage --title "Hacker News front page"

Subscribed: dev/hackernews-frontpage (Hacker News front page)

$ agentfeeds subscribe local/file path=~/notes/project.md \
    --id local/project-notes-md \
    --title "Project notes"

Subscribed: local/project-notes-md (Project notes)

$ agentfeeds status

dev/hackernews-frontpage: Hacker News front page, fresh, ok
local/project-notes-md path=~/notes/project.md: Project notes, fresh, ok

$ sed -n '1,80p' ~/.agentfeeds/catalog.md

# Agent Feeds - Active Subscriptions

## Hacker News front page
- ID: dev/hackernews-frontpage
- Provider: dev/hackernews-frontpage
- Path: state/hn.algolia.com/frontpage.json
- Stale: no
- Mode: event

## Project notes
- ID: local/project-notes-md
- Provider: local/file
- Path: state/local.file/file.project.md.<hash>.json
- Stale: no
- Mode: snapshot

$ # Now ask Hermes:
$ # "What is on Hacker News right now from Agent Feeds?"

Hermes reads ~/.agentfeeds/catalog.md, locates the HN state file,
and answers from local JSON state before using web search.
```

## Talking points

- **Not memory:** durable facts belong in memory; fresh changing state belongs in feeds.
- **Not prompt stuffing:** only the compact catalog enters the session; bulky JSON is read on demand.
- **Not an RSS reader:** RSS is one provider. Agent Feeds also supports local files, GitHub, calendars, weather, finance data, and approved local commands.
- **Inspectable:** subscriptions, provider definitions, catalog, schemas, and state are plain files.

## Suggested voiceover

> Agents need feeds, not just memory. Agent Feeds lets Hermes subscribe to fresh local and public streams, keep detailed JSON state on disk, and inject only a compact catalog into the prompt. When I ask about Hacker News or my project notes, Hermes reads the relevant local state file instead of making me repeat context or stuffing everything into every session.
