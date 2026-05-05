# Agent Feeds Demo

This is the short launch demo for Agent Feeds v0.1.2.

## Narrative

Agent Feeds should be shown as an interactive agent session, not as a user manually driving the CLI.

A new agent session can inspect compact Agent Feeds metadata through the CLI:

```text
python3 scripts/agentfeeds.py streams list
- mac/calendar-today: Today's Calendar.app agenda
- mac/reminders-pending: Pending Reminders.app items
- mac/mail-unread: Unread Mail.app messages
- local/project-notes-md: Project notes
- dev/my-open-prs: My GitHub pull requests
- weather/santa-clara-current: Santa Clara current weather
```

The user then asks normal questions. The agent decides when to run `python3 scripts/agentfeeds.py streams read <subscription-id> --json` before using web search.

![Agent Feeds interactive session demo](../assets/agentfeeds-demo.gif)

## Demo flow

### 1. Session context

The agent starts with compact stream metadata, not bulky state data.

### 2. Calendar awareness

```text
What is on my calendar today?
```

The agent sees `mac/calendar-today`, reads it through `python3 scripts/agentfeeds.py streams read`, and answers from local state before using any external calendar tool.

### 3. Personal task awareness

```text
What reminders are still open?
```

The agent sees `mac/reminders-pending`, reads it through `python3 scripts/agentfeeds.py streams read`, and summarizes current reminders without asking the user to restate them.

### 4. Local project context

```text
Refresh Project notes and summarize it.
```

The agent refreshes `local/project-notes-md`, reads the refreshed snapshot, and answers from the user's local file.

### 5. Public and developer sources

```text
Anything new from my watched releases, open PRs, or Santa Clara weather?
```

The agent sees active GitHub, RSS, and weather streams, reads only the matching local state files, and reports what changed.

## Talking points

- **Interactive UX:** the user asks natural questions; Agent Feeds is the internal context layer.
- **Compact prompt metadata:** the session sees stream names/IDs, not every state payload.
- **Local state on demand:** the agent reads detailed JSON only when relevant.
- **Not memory:** durable facts belong in memory; fresh changing state belongs in feeds.
- **Inspectable:** the CLI reports stream metadata and state paths for debugging without requiring raw file reads in normal agent flow.

## Suggested voiceover

> Agent Feeds is most useful inside an agent session. The agent can inspect a compact list of local streams - calendar, reminders, unread mail, project notes, GitHub, RSS, and weather - without loading all the raw data. When I ask a normal question, it notices the relevant stream, reads it through the Agent Feeds CLI, and answers from fresh inspectable context before using web search.
