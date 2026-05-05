# AgentFeeds Registry Submission Guide

Goal: publish AgentFeeds where agent builders/operators discover skills, then convert listings into feedback, not vanity stars.

Core promise:

```text
AgentFeeds is a ready-to-read context cache for personal agents. It keeps fresh local context warm on disk so agents can read relevant stream state before scanning skills, searching the web, re-fetching APIs, or asking users to repeat context.
```

Primary CTA:

```text
Install the skill, ask your agent to set up useful default streams, then tell me: what is the first local/private source your agent should subscribe to?
```

## Submission Priority

### Tier 1: submit first

1. LobeHub Skills Marketplace
   - URL: https://lobehub.com/skills
   - Why: broad agent-skill marketplace, supports SKILL.md bundles, lists Hermes/Claude Code/Codex/OpenCode-style agents.
   - Category fit: Productivity & Tasks, Self-Hosted & Automation, Notes & PKM, Calendar & Scheduling, Apple Apps & Services.
   - Action: use the site Submit Skill button or equivalent GitHub flow.

2. Anthropic public Agent Skills repository
   - URL: https://github.com/anthropics/skills
   - Why: canonical high-attention Agent Skills repo.
   - Caveat: likely high PR volume and stricter expectations; submit after LobeHub copy is solid.
   - Action: inspect CONTRIBUTING/template, fork, add AgentFeeds skill bundle or example, open PR.

3. Claude Code / plugin marketplace surfaces
   - Docs: https://code.claude.com/docs/plugin-marketplace
   - Why: AgentFeeds fits as an agent-facing skill/plugin: install once, then prompt the agent.
   - Action: package the existing skill/plugin metadata into the expected marketplace format.

### Tier 2: submit after first feedback

4. Community Claude Skills marketplaces/directories
   - Examples found by search: claudeskillsmarket.com, claudemarketplaces.com, beshkenadze/claude-skills-marketplace.
   - Why: lower authority but easy distribution.
   - Action: submit only if the listing path takes <20 minutes.

5. Awesome lists / GitHub topic discovery
   - Search GitHub for active awesome lists around Claude Skills, agent skills, AI agents, personal agents, context engineering, local-first AI.
   - Why: long-tail discovery.
   - Action: submit PRs only to active repos with recent commits.

6. Hacker News / Reddit / Discord communities
   - Not a registry, but often higher feedback density than directories.
   - Action: post after at least one marketplace listing is live.

## Canonical Listing Copy

Short description, <=160 chars:

```text
Ready-to-read context cache for personal agents: calendars, inbox, GitHub, RSS, notes, dashboards, and local streams kept fresh on disk.
```

One-liner:

```text
Don’t make agents hunt for context. Keep it ready.
```

Long description:

```text
AgentFeeds is a ready-to-read context cache for personal agents. It keeps changing context warm on disk — calendars, inboxes, reminders, GitHub, RSS/news, weather, notes, dashboards, local files, and approved local sources — so agents can read compact local stream state before scanning skills, searching the web, re-fetching APIs, or asking users to repeat context. Memory stores durable facts; AgentFeeds stores fresh, timestamped, refreshable state that agents can search, read, refresh, and summarize only when relevant.
```

Tags:

```text
ai-agents, agent-skills, personal-agents, context-engineering, local-first, productivity, automation, calendar, inbox, rss, github, macos, hermes, claude-code, codex, opencode
```

Primary repo:

```text
https://github.com/verkyyi/agentfeeds
```

Release / install URL:

```text
https://github.com/verkyyi/agentfeeds/releases/tag/skill-v0.1.2
```

Release asset:

```text
agentfeeds-skill-v0.1.2.zip
```

Demo asset:

```text
assets/agentfeeds-demo.gif
```

## Agent-Facing Try Prompts

Use one prompt per box in listings where possible:

```text
Set up AgentFeeds with useful safe default streams for this agent.
```

```text
What fresh context does AgentFeeds already have available?
```

```text
Use AgentFeeds first. What should I pay attention to today?
```

```text
Subscribe AgentFeeds to my calendar, reminders, unread mail, GitHub activity, and a few AI news sources.
```

```text
Before searching the web, check AgentFeeds for relevant cached context.
```

## Feedback Prompt

Use this in PR descriptions, listing descriptions, DMs, and launch posts:

```text
I’m looking for feedback from people running personal/local agents: what is the first local or private source you would want your agent to subscribe to and keep ready — calendar, inbox, GitHub, notes, finance, dashboards, messages, something else?
```

## Submission Checklist

Before each submission:

- [ ] Repo main branch is clean and pushed.
- [ ] README opens with the ready-to-read cache promise.
- [ ] Install/release link works.
- [ ] Demo GIF renders.
- [ ] Skill bundle version matches README/SKILL.md/pyproject/release asset.
- [ ] Natural-language try prompts are visible before CLI commands.
- [ ] Listing asks for feedback, not just stars.

After each submission:

- [ ] Record URL, date, status, and any reviewer notes below.
- [ ] Reply quickly to install failures or requested source types.
- [ ] Add requested source types to feedback log; do not build immediately unless multiple people ask or one committed user is blocked.

## Submission Tracker

| Target | Status | URL | Notes |
| --- | --- | --- | --- |
| LobeHub Skills Marketplace | todo | https://lobehub.com/skills | First priority. |
| Anthropic skills repo | todo | https://github.com/anthropics/skills | Inspect contribution flow before PR. |
| Claude Code plugin marketplace | todo | https://code.claude.com/docs/plugin-marketplace | Package host metadata if needed. |
| claudeskillsmarket.com | maybe | https://www.claudeskillsmarket.com | Submit if low friction. |
| claudemarketplaces.com | maybe | https://claudemarketplaces.com | Submit if low friction. |
| beshkenadze/claude-skills-marketplace | maybe | https://github.com/beshkenadze/claude-skills-marketplace | Low stars, lower priority. |

## Constraint

Spend no more than 2 hours on registry mechanics before doing direct outreach. The useful metric is feedback/install attempts, not number of directory entries.
