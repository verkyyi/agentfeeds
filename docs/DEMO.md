# Agent Feeds Demo

This is the short launch demo for Agent Feeds v0.1.0.

## Narrative

Agent Feeds should be shown as an interactive Hermes session, not as a user manually driving the CLI.

A new Hermes session can inspect compact Agent Feeds metadata through the CLI:

```text
python3 scripts/agentfeeds.py streams list
- weather/santa-clara-current: Santa Clara current weather
- dev/hackernews-frontpage: Hacker News front page
- finance/quote-btc: BTC quote
- news/openai-com: OpenAI News
- ops/hermes-gateway-health: Hermes gateway health
```

The user then asks normal questions. Hermes decides when to run `python3 scripts/agentfeeds.py streams read <subscription-id> --json` before using web search.

![Agent Feeds interactive session demo](../assets/agentfeeds-demo.gif)

## Demo flow

### 1. Session context

Hermes starts with compact stream metadata, not bulky state data.

### 2. Current news

```text
What is on Hacker News right now?
```

Hermes sees `dev/hackernews-frontpage`, reads it through `python3 scripts/agentfeeds.py streams read`, and answers from the fresh snapshot before web search.

### 3. Personal ops awareness

```text
Is my Hermes gateway healthy?
```

Hermes sees `ops/hermes-gateway-health`, reads it through `python3 scripts/agentfeeds.py streams read`, and reports the current status.

### 4. Market and weather snapshots

```text
What are BTC and MSFT doing, and what is Santa Clara weather?
```

Hermes sees the quote and weather streams, reads the relevant snapshots, and summarizes them together.

### 5. Followed AI sources

```text
Anything new from OpenAI, Anthropic, or Hermes Agent releases?
```

Hermes sees active RSS/release streams, reads their local event files, and reports what changed.

## Talking points

- **Interactive UX:** the user asks Hermes natural questions; Agent Feeds is the internal context layer.
- **Compact prompt metadata:** the session sees stream names/IDs, not every state payload.
- **Local state on demand:** Hermes reads detailed JSON only when relevant.
- **Not memory:** durable facts belong in memory; fresh changing state belongs in feeds.
- **Inspectable:** the CLI reports stream metadata and state paths for debugging without requiring raw file reads in normal agent flow.

## Suggested voiceover

> Agent Feeds is most useful inside an agent session. Hermes can inspect a compact list of local streams — weather, Hacker News, market quotes, OpenAI news, gateway health — without loading all the raw data. When I ask a normal question, Hermes notices the relevant stream, reads it through the Agent Feeds CLI, and answers from fresh inspectable context before using web search.
